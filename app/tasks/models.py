from django.db import models
from users.models import User # Assuming User is correctly imported

class TeamList(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_lists')

    class Meta:
        verbose_name = "Список команды"
        verbose_name_plural = "Списки команд"
        
    def __str__(self):
        return self.name

class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    list = models.ForeignKey(TeamList, on_delete=models.CASCADE, related_name='tasks')
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tasks_assigned')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks_created')
    
    due_date = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date', '-created_at']
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"

    def __str__(self):
        return self.title