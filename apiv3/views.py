from rest_framework import viewsets, generics, status, pagination, mixins, permissions
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .serializers import *
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from rest_framework.decorators import action
from judge.models import (
    Contest, ContestParticipation, ContestTag, Judge, Language, Organization, Problem, ProblemType, Profile, Rating,
    Submission, ContestSubmission, SubmissionSource,
)
from judge.views.problem import (
    ProblemMixin, TitleMixin,
)
from judge.views.submission import group_test_cases, combine_statuses
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

# User = get_user_model()

class AuthRegister(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

    @transaction.atomic
    def post(self, request, format=None):
        serializer = ProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserInfoViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    # def get(self, request, pk, format=None):
    #     """
    #         ユーザーをリストアップする
    #     """
    #     latest_rating_subquery = Rating.objects.filter(user=OuterRef('pk')).order_by('-contest__end_time')

    #     users = Profile.objects.filter(is_unlisted=False, user__is_active=True).annotate(
    #         username=F('user__username'),
    #         latest_rating=Subquery(latest_rating_subquery.values('rating')[:1]),
    #     ).order_by('id').only('id', 'points', 'performance_points', 'problem_count', 'display_rank')

    #     data = [{
    #         'id': profile.id,
    #         'username': profile.username,
    #         'points': profile.points,
    #         'performance_points': profile.performance_points,
    #         'problem_count': profile.problem_count,
    #         'rank': profile.display_rank,
    #         'rating': profile.latest_rating,
    #     } for profile in users]
    #     return Response(data, status=status.HTTP_200_OK)

    # def delete(self, request, **kwargs):
    #     """
    #         メンバーを削除する
    #     """
    #     projid = kwargs.get('pk')
    #     userid = kwargs.get('user')
    #     projmember = ProjectToUsers.objects.get(project=projid, user=userid)
    #     projmember.delete()
    #     return Response({"status": "deleted"}, status=status.HTTP_200_OK)

class SubmitData(generics.GenericAPIView, ProblemMixin, TitleMixin):
    # queryset = User.objects.all()
    # serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        # get the problem
        problem = Problem.objects.get(pk=request.data["problem"])
        print("hoge", request.data)
        #---
        if (
            not self.request.user.has_perm('judge.spam_submission') and
            Submission.objects.filter(user=self.request.user, rejudged_date__isnull=True)
                              .exclude(status__in=['D', 'IE', 'CE', 'AB']).count() >= settings.DMOJ_SUBMISSION_LIMIT
        ):
            return Response(data={"status": 'You submitted too many submissions.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS)
        if not problem.allowed_languages.filter(id=request.data["language"]).exists():
            raise PermissionDenied()
        if not self.request.user.is_superuser and problem.banned_users.filter(id=self.request.user.id).exists():
            return Response(data={"status": 'Banned from submitting'},
                status=status.HTTP_400_BAD_REQUEST)
        # Must check for zero and not None. None means infinite submissions remaining.
        # if self.remaining_submission_count == 0:
        #     return Response(data={"status": 'Too many submissions'},
        #         status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            serializer = SubmissionSerializer(data=request.data)
            # self.new_submission.user = request.user.id
            # self.new_submission.save()
            if serializer.is_valid():
                self.new_submission = serializer.save(user_id=request.user.id)
                source = SubmissionSource(submission=self.new_submission, source=request.data['source'])
                source.save()
                # Save a query.
            else:
                print(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.new_submission.source = source
        self.new_submission.judge(force_judge=True)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

class SubmissionStatus(generics.GenericAPIView):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        pid = self.kwargs["pk"]
        submission = Submission.objects.get(id=pid)
        # print(submission)

        cases = []
        for batch in group_test_cases(submission.test_cases.all())[0]:
            batch_cases = [
                {
                    'type': 'case',
                    'case_id': case.case,
                    'status': case.status,
                    'time': case.time,
                    'memory': case.memory,
                    'points': case.points,
                    'total': case.total,
                } for case in batch['cases']
            ]

            # These are individual cases.
            if batch['id'] is None:
                cases.extend(batch_cases)
            # This is one batch.
            else:
                cases.append({
                    'type': 'batch',
                    'batch_id': batch['id'],
                    'cases': batch_cases,
                    'points': batch['points'],
                    'total': batch['total'],
                })

        context = {
            'id': submission.id,
            'problem': submission.problem.code,
            'user': submission.user.user.username,
            'date': submission.date.isoformat(),
            'time': submission.time,
            'memory': submission.memory,
            'points': submission.points,
            'language': submission.language.key,
            'status': submission.status,
            'result': submission.result,
            'case_points': submission.case_points,
            'case_total': submission.case_total,
            'cases': cases,
            'error': submission.error,
        }

        return Response(context, status=status.HTTP_200_OK)

class UserDetail(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        pid = self.kwargs["pk"]
        profile = Profile.objects.get(username=pid)

        solved_problems = list(
            Submission.objects
            .filter(
                result='AC',
                user=profile,
                problem__is_public=True,
                problem__is_organization_private=False,
            )
            .values('problem').distinct()
            .values_list('problem__code', flat=True),
        )

        last_rating = profile.ratings.order_by('-contest__end_time').first()

        contest_history = []
        participations = (
            ContestParticipation.objects
            .filter(
                user=profile,
                virtual=ContestParticipation.LIVE,
                contest__in=Contest.get_visible_contests(self.request.user),
                contest__end_time__lt=self._now,
            )
            .order_by('contest__end_time')
        )
        for contest_key, score, cumtime, rating, mean, performance in participations.values_list(
            'contest__key', 'score', 'cumtime', 'rating__rating', 'rating__mean', 'rating__performance',
        ):
            contest_history.append({
                'key': contest_key,
                'score': score,
                'cumulative_time': cumtime,
                'rating': rating,
                'raw_rating': mean,
                'performance': performance,
            })

        context = {
            'id': profile.id,
            'username': profile.user.username,
            'points': profile.points,
            'performance_points': profile.performance_points,
            'problem_count': profile.problem_count,
            'solved_problems': solved_problems,
            'rank': profile.display_rank,
            'rating': last_rating.rating if last_rating is not None else None,
            'organizations': list(profile.organizations.values_list('id', flat=True)),
            'contests': contest_history,
        }

        return Response(context, status=status.HTTP_200_OK)

class ContestInfoViewSet(viewsets.ModelViewSet):
    queryset = Contest.objects.all()
    serializer_class = ContestSerializer
    permission_classes = [IsAuthenticated]


class ProblemViewSet(viewsets.ModelViewSet):
    queryset = Problem.objects.all()
    serializer_class = ProblemSerializer
    permission_classes = [IsAuthenticated]

class JudgeViewSet(viewsets.ModelViewSet):
    queryset = Judge.objects.all()
    serializer_class = JudgeSerializer
    permission_classes = [IsAuthenticated]
