from celery import shared_task
from reviewzip.models import Review

@shared_task
def increase_watch(review_id):
    review = Review.objects.only('watch').get(id=review_id)
    review.watch += 1
    review.save()