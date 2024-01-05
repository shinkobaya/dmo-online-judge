from rest_framework import serializers, mixins
from django.contrib.auth import get_user_model
from judge.models import (
    Contest, ContestParticipation, ContestTag, Judge, Language, Organization, Problem, ProblemType, Profile, Rating,
    Submission, SubmissionTestCase
)
from django.utils import timezone
User = get_user_model()

class LanguageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Language
        fields = ('id', 'key', 'name')

class JudgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Judge
        fields = ('id', 'name')

class SubmissionSerializer(serializers.ModelSerializer):
    # source = serializers.CharField(max_length=65536)
    # judge = ChoiceField(choices=(), widget=forms.HiddenInput(), required=False)
    # judged_on_id = serializers.CharField(max_length=100)

    class Meta:
        model = Submission
        fields = ('id', 'language', 'problem', )
        read_only_fields = ['id']

class ProfileSerializer(serializers.ModelSerializer):
    """
        プロセスの項目
    """
    class Meta:
        model = Profile
        fields = ('id', 'username', 'points', 'performance_points', 'problem_count', 'display_rank', 'rating')

    def create(self, validated_data):
        now = timezone.now()
        if not validated_data['email']:
            raise ValueError('Users must have an email address.')

        user, _ = User.objects.get_or_create(
            username=validated_data['username'],
            email=self.normalize_email(validated_data['email']),
            is_active=True,
            last_login=now,
            date_joined=now,
        )
        user.set_password(validated_data['password'])
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user, defaults={
            'language': Language.get_default_language(),
        })

        # profile.timezone = validated_data['timezone']
        # profile.language = validated_data['language']
        # profile.organizations.add(*validated_data['organizations'])
        profile.save()

        # if newsletter_id is not None and cleaned_data['newsletter']:
        #     Subscription(user=user, newsletter_id=newsletter_id, subscribed=True).save()
        return profile
        # return Profile.objects.create_user(request_data=validated_data)

class ProblemSerializer(serializers.ModelSerializer):
    allowed_languages = LanguageSerializer(read_only=True, many=True)

    class Meta:
        model = Problem
        fields = ('pk', 'code', 'name', 'description', 'allowed_languages')

class ContestSerializer(serializers.ModelSerializer):
    problems = ProblemSerializer(read_only=True, many=True)

    class Meta:
        model = Contest
        fields = ('pk', 'key', 'name', 'problems')

class SubmissionTestcaseSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubmissionTestCase
        fields = ('case', 'status', 'time', 'memory', 'points',
                  'total', 'batch', 'feedback', 'extended_feedback', 'output')
