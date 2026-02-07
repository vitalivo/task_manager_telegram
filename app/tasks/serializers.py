from rest_framework import serializers

from .models import Client, Task, TaskComment, TeamList, TaskAuditLog
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
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id',
            'title',
            'description',
            'list',
            'list_name',
            'assigned_to',
            'assigned_to_id',
            'due_date',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'is_completed',
            'created_at',
            'updated_at',
            'started_at',
            'completed_at',
            'estimate_hours',
            'actual_hours',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'assigned_to', 'started_at', 'completed_at']

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


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'contact_person', 'phone', 'email', 'telegram', 'notes']


class ProjectSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source='client',
        write_only=True,
        required=False,
        allow_null=True,
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model = TeamList
        fields = [
            'id',
            'name',
            'description',
            'status',
            'status_display',
            'source',
            'source_display',
            'price',
            'start_date',
            'deadline',
            'rejected_reason',
            'client',
            'client_id',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'client']


class TaskCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author_username', 'text', 'created_at']
        read_only_fields = ['id', 'created_at', 'author_username']


class TaskAuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)

    class Meta:
        model = TaskAuditLog
        fields = ['id', 'task', 'actor_username', 'action', 'details', 'created_at']
        read_only_fields = ['id', 'created_at', 'actor_username']