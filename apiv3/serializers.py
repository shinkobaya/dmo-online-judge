from rest_framework import serializers, mixins
from django.contrib.auth import get_user_model
from judge.models import (
    Contest, ContestParticipation, ContestTag, Judge, Language, Organization, Problem, ProblemType, Profile, Rating,
    Submission, SubmissionTestCase
)
from django.utils import timezone
from django.contrib.auth.password_validation import get_default_password_validators
from django.core.exceptions import ValidationError

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
        fields = ('id', 'language', 'problem', 'judged_date')
        read_only_fields = ['id', 'judged_date']

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

class ProblemTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProblemType
        fields = ('name', 'full_name')

class ProblemSerializer(serializers.ModelSerializer):
    allowed_languages = LanguageSerializer(read_only=True, many=True)
    types = ProblemTypeSerializer(read_only=True, many=True)

    class Meta:
        model = Problem
        fields = ('pk', 'code', 'name', 'description', 'allowed_languages', 'types')

class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContestTag
        fields = ('name', 'color', 'description')

class ContestSerializer(serializers.ModelSerializer):
    problems = ProblemSerializer(read_only=True, many=True)
    tags = TagSerializer(read_only=True, many=True)

    class Meta:
        model = Contest
        fields = ('pk', 'key', 'name', 'problems', 'description', 'tags')

class SubmissionTestcaseSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubmissionTestCase
        fields = ('case', 'status', 'time', 'memory', 'points',
                  'total', 'batch', 'feedback', 'extended_feedback', 'output')

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', )
        # レスポンスにパスワードを含めないようにする
        extra_kwargs = {'password': {'write_only': True}}
        read_only_fields = ['id', ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
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

        return user

def validate_password(password, user=None, password_validators=None):
    """
    Validate that the password meets all validator requirements.

    If the password is valid, return ``None``.
    If the password is invalid, raise ValidationError with all error messages.
    """
    errors = []
    if password_validators is None:
        password_validators = get_default_password_validators()
    for validator in password_validators:
        try:
            validator.validate(password, user)
        except ValidationError as error:
            errors.append(error)
    if errors:
        raise serializers.ValidationError(errors)

class ChangePasswordSerializer(serializers.Serializer):
    """パスワード変更用Serializer"""

    oldPassword = serializers.CharField(max_length=255)
    """現在のパスワード"""
    newPassword = serializers.CharField(max_length=255)
    """新規パスワード"""
    confirmPassword = serializers.CharField(max_length=255)
    """新規パスワード再確認"""

    def validate(self, data):
        if data["newPassword"] != data["confirmPassword"]:
            raise serializers.ValidationError("新規パスワードと確認パスワードが違います")
        validate_password(data["newPassword"])
        return data


class ResetPasswordSerializer(serializers.Serializer):
    """パスワード再設定用シリアライザ"""

    token = serializers.CharField(max_length=255)
    """パスワード再設定メールURL用トークン"""
    newPassword = serializers.CharField(max_length=255)
    """新規パスワード"""
    confirmPassword = serializers.CharField(max_length=255)
    """新規パスワード再確認"""

    def validate(self, data):
        if data["newPassword"] != data["confirmPassword"]:
            raise serializers.ValidationError("新規パスワードと確認パスワードが違います")
        validate_password(data["newPassword"])
        # errors = validate_password(data["newPassword"])
        # print("res")
        # if errors:
        #     raise serializers.ValidationError("複雑なパスワードを設定してください。")
        return data


class CheckTokenSerializer(serializers.Serializer):
    """トークンが有効であるか確認するSerializer"""

    token = serializers.CharField(max_length=255)
    """トークン"""
