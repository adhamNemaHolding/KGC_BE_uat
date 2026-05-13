from .models import Course
from .serializers import CourseSerializer


def create_course(data: dict) -> Course:
    serializer = CourseSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.save()
