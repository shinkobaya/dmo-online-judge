from collections import defaultdict

from django.core.cache import cache
from django.db.models import F, Count, Max, Q
from django.utils import timezone
from django.utils.translation import ugettext as _

from judge.models import Submission, Problem

__all__ = ['contest_completed_ids', 'user_completed_ids', 'user_authored_ids', 'user_editable_ids']


def user_authored_ids(profile):
    result = set(Problem.objects.filter(authors=profile).values_list('id', flat=True))
    return result


def user_editable_ids(profile):
    result = set((Problem.objects.filter(authors=profile) | Problem.objects.filter(curators=profile)).values_list('id',
                                                                                                                  flat=True))
    return result


def contest_completed_ids(participation):
    key = 'contest_complete:%d' % participation.id
    result = cache.get(key)
    if result is None:
        result = set(participation.submissions.filter(submission__result='AC', points=F('problem__points'))
                     .values_list('problem__problem__id', flat=True).distinct())
        cache.set(key, result, 86400)
    return result


def user_completed_ids(profile):
    key = 'user_complete:%d' % profile.id
    result = cache.get(key)
    if result is None:
        result = set(Submission.objects.filter(user=profile, result='AC', points=F('problem__points'))
                     .values_list('problem_id', flat=True).distinct())
        cache.set(key, result, 86400)
    return result


def contest_attempted_ids(participation):
    key = 'contest_attempted:%s' % participation.id
    result = cache.get(key)
    if result is None:
        result = {id: {'achieved_points': points, 'max_points': max_points}
                  for id, max_points, points in (participation.submissions
                                                 .values_list('problem__problem__id', 'problem__points')
                                                 .annotate(points=Max('points'))
                                                 .filter(points__lt=F('problem__points')))}
        cache.set(key, result, 86400)
    return result


def user_attempted_ids(profile):
    key = 'user_attempted:%s' % profile.id
    result = cache.get(key)
    if result is None:
        result = {id: {'achieved_points': points, 'max_points': max_points}
                  for id, max_points, points in (Submission.objects.filter(user=profile)
                                                 .values_list('problem__id', 'problem__points')
                                                 .annotate(points=Max('points'))
                                                 .filter(points__lt=F('problem__points')))}
        cache.set(key, result, 86400)
    return result


def get_result_table(*args, **kwargs):
    if args:
        submissions = args[0]
        if kwargs:
            raise ValueError(_("Can't pass both queryset and keyword filters"))
    else:
        submissions = Submission.objects.filter(**kwargs) if kwargs is not None else Submission.objects
    raw = submissions.values('result').annotate(count=Count('result')).values_list('result', 'count')
    results = defaultdict(int, raw)
    return [(_('Accepted'), 'AC', results['AC']),
            (_('Wrong Answer'), 'WA', results['WA']),
            (_('Compile Error'), 'CE', results['CE']),
            (_('Time Limit Exceeded'), 'TLE', results['TLE']),
            (_('Memory Limit Exceeded'), 'MLE', results['MLE']),
            (_('Other'), 'OTH', results['RTE'] + results['IR'] + results['OLE'] + results['AB'] + results['IE']),
            (_('Total'), 'TOT', sum(results.values()))]


def editable_problems(user, profile=None):
    subquery = Problem.objects.all()
    if profile is None:
        profile = user.profile
    if not user.has_perm('judge.edit_all_problem'):
        subfilter = Q(authors__id=profile.id) | Q(curators__id=profile.id)
        if user.has_perm('judge.edit_public_problem'):
            subfilter |= Q(is_public=True)
        subquery = subquery.filter(subfilter)
    return subquery


def hot_problems(duration, limit):
    cache_key = 'hot_problems:%d:%d' % (duration.total_seconds(), limit)
    queryset = cache.get(cache_key)
    if queryset is None:
        queryset = Problem.objects.filter(is_public=True, submission__date__gt=timezone.now() - duration) \
            .annotate(count=Count('submission__user', distinct=True)).order_by('-count').defer('description')[:limit]
        cache.set(cache_key, queryset, 900)
    return queryset
