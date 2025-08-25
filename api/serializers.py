from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import Question, UserStats

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'first_name', 'last_name', 'role')
        extra_kwargs = {
            'role': {'read_only': True} # Users can't set their own role on registration. Default is 'user'.
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data retrieval.
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role')

class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'), username=username, password=password)
            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Must include "username" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        data['user'] = user
        return data

class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for the Question model.
    """
    class Meta:
        model = Question
        fields = '__all__'

class UserStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserStats model.
    """
    accuracy = serializers.FloatField(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserStats
        fields = ('user', 'exams_taken', 'total_questions_answered', 'correct_answers', 'accuracy')
