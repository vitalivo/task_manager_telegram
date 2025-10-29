from rest_framework import serializers
from .models import Task, TeamList
from users.models import UserProfile

class UserMinimalSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)

class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserMinimalSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=Task.assigned_to.field.related_model.objects.all(), 
        source='assigned_to', write_only=True, required=False
    )
    list_name = serializers.CharField(source='list.name', read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'list', 'list_name', 'assigned_to', 'assigned_to_id', 'due_date', 'is_completed', 'created_at']
        read_only_fields = ['id', 'created_at', 'assigned_to']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

# ДОБАВЛЯЕМ НОВЫЕ СЕРИАЛИЗАТОРЫ ДЛЯ ЛИЧНЫХ БОТОВ
class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['username', 'telegram_chat_id', 'personal_bot_token', 'personal_bot_username']

class PersonalBotSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    username = serializers.CharField(required=False, allow_blank=True)