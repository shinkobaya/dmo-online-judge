from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class UserResetPassword(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        # db_comment="システムユーザID",
    )
    token = models.CharField(
        max_length=255,
        # db_comment="パスワード設定メールURL用トークン",
    )
    expiry = models.DateTimeField(
        null=True,
        default=None,
        # db_comment="有効期限",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        # db_comment="作成日時",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="user_password_reset",
        # db_comment="ユーザテーブル外部キー",
    )
    is_used = models.BooleanField(
        default=False,
        # db_comment="使用有無",
    )

    class Meta:
        db_table = "PasswordReset"
        # db_table_comment = "ユーザパスワード再設定"
