from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User
from apps.core.choices import Role, UserStatus
from apps.core.exceptions import BusinessRuleError


class UserSerializer(serializers.ModelSerializer):
    roll_number = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source="date_joined", read_only=True)
    last_login_at = serializers.DateTimeField(source="last_login", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "name",
            "role",
            "status",
            "email",
            "phone",
            "avatar_url",
            "roll_number",
            "created_at",
            "last_login_at",
        ]

    def get_roll_number(self, obj):
        return obj.member.roll_number if obj.member_id else None


class LoginSerializer(TokenObtainPairSerializer):
    """Extends simplejwt's obtain-pair serializer with a custom-claim token and a
    pre-check for suspended accounts (so the error message matches the frontend's
    "This account is suspended" rather than a generic auth failure).
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["name"] = user.name
        token["rollNumber"] = user.member.roll_number if user.member_id else None
        return token

    def validate(self, attrs):
        username = attrs.get(self.username_field)
        candidate = User.objects.filter(**{f"{self.username_field}__iexact": username}).first()
        if candidate is not None and candidate.status == UserStatus.SUSPENDED:
            raise BusinessRuleError(
                "ACCOUNT_SUSPENDED", "This account is suspended. Please contact the administrator."
            )
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "email", "phone", "avatar_url"]
        extra_kwargs = {field: {"required": False} for field in fields}


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "Current password is incorrect."})
        return attrs


class AdminUserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    roll_number = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "password", "name", "role", "status", "email", "phone", "roll_number"]

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", None))
        roll_number = attrs.get("roll_number")
        if role == Role.STUDENT and not roll_number and self.instance is None:
            raise serializers.ValidationError({"roll_number": "Required when role is student."})
        return attrs

    def create(self, validated_data):
        from apps.members.models import Member

        password = validated_data.pop("password", None)
        roll_number = validated_data.pop("roll_number", None)
        member = Member.objects.get(roll_number=roll_number) if roll_number else None
        user = User(member=member, **validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        validated_data.pop("roll_number", None)
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
