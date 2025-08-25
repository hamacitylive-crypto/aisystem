import os
import json
import fitz  # PyMuPDF
import google.generativeai as genai
from datetime import datetime, timedelta

from django.contrib.auth import login, logout, get_user_model
from django.db.models import Count, F
from django.db.models.functions import TruncDate
from django.conf import settings
from django.utils import timezone

from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action

from .models import Question, UserStats
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    LoginSerializer,
    QuestionSerializer,
    UserStatsSerializer
)
from .permissions import IsAdmin

User = get_user_model()

# Configure the Gemini API client
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

# --- Authentication Endpoints ---

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer
    throttle_scope = 'register'

class LoginView(APIView):
    permission_classes = (AllowAny,)
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

class UserView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


# --- Question Generation Endpoint ---

class GenerateQuestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        content_type = request.content_type
        prompt_context = ""
        params = {}

        if 'multipart/form-data' in content_type:
            pdf_file = request.FILES.get('pdf_file')
            if not pdf_file:
                return Response({"error": "PDF file is required for multipart/form-data."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                for page in doc:
                    prompt_context += page.get_text()
                doc.close()
                params = request.POST
            except Exception as e:
                return Response({"error": f"Error processing PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else: # application/json
            prompt_context = request.data.get('topic', '')
            params = request.data

        specialization = params.get('specialization', 'Software Engineering')
        num_questions = params.get('num_questions', 5)
        question_type = params.get('type', 'Multiple Choice')

        if not genai.API_KEY:
             return Response({"error": "GEMINI_API_KEY not configured on the server."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        prompt = f"""
        Based on the following context and parameters, generate an exam.
        Context: "{prompt_context if prompt_context else 'General Knowledge'}"
        Specialization: {specialization}
        Number of Questions: {num_questions}
        Question Type: {question_type}

        Generate a JSON array of question objects. Each object must have these exact keys: "question", "options", "answer".
        - "question": The question text (string).
        - "options": An array of 4 strings for Multiple Choice, an array of ["True", "False"] for True/False, or an empty array for Short Answer.
        - "answer": The correct answer (string).

        Example for Multiple Choice:
        {{
            "question": "What is Python?",
            "options": ["A snake", "A programming language", "A car", "A fruit"],
            "answer": "A programming language"
        }}

        Return ONLY the JSON array, with no other text or explanations.
        """

        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)

            # Clean the response to get only the JSON part.
            json_text = response.text.strip().replace('```json', '').replace('```', '').strip()
            generated_questions = json.loads(json_text)

            questions_to_create = []
            for q_data in generated_questions:
                questions_to_create.append(Question(
                    question=q_data.get('question'),
                    type=question_type,
                    specialization=specialization,
                    options=q_data.get('options', []),
                    answer=q_data.get('answer'),
                    is_generated=True,
                    creator=request.user
                ))

            Question.objects.bulk_create(questions_to_create)
            serializer = QuestionSerializer(questions_to_create, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"Failed to generate questions from AI model: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Question Bank Endpoints ---

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['list', 'batch_update', 'clear', 'destroy', 'update', 'partial_update']:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], url_path='add-generated')
    def add_generated(self, request):
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)
        # Add creator to each question instance before saving
        questions = serializer.save(creator=request.user, is_generated=True)
        return Response(QuestionSerializer(questions, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='clear')
    def clear(self, request):
        count, _ = Question.objects.filter(is_generated=True).delete()
        return Response({"detail": f"Successfully deleted {count} AI-generated questions."}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='standard')
    def standard(self, request):
        specialization = request.query_params.get('specialization')
        num_questions = int(request.query_params.get('num_questions', 10))

        if not specialization:
            return Response({"error": "Specialization parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        questions = Question.objects.filter(
            is_generated=False,
            specialization=specialization
        ).order_by('?')[:num_questions]

        serializer = self.get_serializer(questions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='batch-update')
    def batch_update(self, request):
        # A simple implementation: assumes a list of question objects
        # A more robust version would handle create vs update logic
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- User Statistics Endpoints ---

class UserStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        stats, created = UserStats.objects.get_or_create(user=request.user)
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='update')
    def update_stats(self, request):
        score = request.data.get('score')
        total_questions = request.data.get('total_questions')

        if score is None or total_questions is None:
            return Response({"error": "Score and total_questions are required."}, status=status.HTTP_400_BAD_REQUEST)

        stats = UserStats.objects.get(user=request.user)
        stats.exams_taken = F('exams_taken') + 1
        stats.total_questions_answered = F('total_questions_answered') + total_questions
        stats.correct_answers = F('correct_answers') + score
        stats.save()
        stats.refresh_from_db() # Get the updated values from the database

        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='reset')
    def reset_stats(self, request):
        stats = UserStats.objects.get(user=request.user)
        stats.exams_taken = 0
        stats.total_questions_answered = 0
        stats.correct_answers = 0
        stats.save()

        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)


# --- Admin Panel Endpoints ---

class AdminDashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        total_users = User.objects.count()
        total_questions = Question.objects.count()

        # Registration trends for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        registration_trends = User.objects.filter(date_joined__gte=thirty_days_ago) \
            .annotate(date=TruncDate('date_joined')) \
            .values('date') \
            .annotate(count=Count('id')) \
            .order_by('date')

        # Question type distribution
        question_type_distribution = Question.objects.values('type') \
            .annotate(count=Count('type')) \
            .order_by('type')

        # Recent users
        recent_users = User.objects.order_by('-date_joined')[:5]
        recent_users_serializer = UserSerializer(recent_users, many=True)

        dashboard_data = {
            "total_users": total_users,
            "total_questions": total_questions,
            "ai_generated_questions": Question.objects.filter(is_generated=True).count(),
            "manual_questions": Question.objects.filter(is_generated=False).count(),
            "registration_trends": list(registration_trends),
            "question_type_distribution": list(question_type_distribution),
            "recent_users": recent_users_serializer.data,
        }
        return Response(dashboard_data)

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
