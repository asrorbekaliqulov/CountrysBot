"""
Foydalanuvchi fikr va baholash modeli
"""
from django.db import models
from django.utils.timezone import now
from apps.Bot.models.TelegramBot import TelegramUser


class Feedback(models.Model):
    """
    Foydalanuvchi fikr va baholash modeli.
    Bir foydalanuvchi ko'p marta baholashi mumkin, lekin o'rtacha bahosi hisoblanadi.
    """
    RATING_CHOICES = [
        (1, '⭐'),
        (2, '⭐⭐'),
        (3, '⭐⭐⭐'),
        (4, '⭐⭐⭐⭐'),
        (5, '⭐⭐⭐⭐⭐'),
    ]

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='feedbacks',
        verbose_name='Foydalanuvchi'
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        null=True,
        blank=True,
        verbose_name='Baholash (1-5)'
    )
    text = models.TextField(
        blank=True,
        null=True,
        verbose_name='Fikr matni'
    )
    is_suggestion_only = models.BooleanField(
        default=False,
        verbose_name='Faqat taklif'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yaratilgan sana'
    )

    class Meta:
        db_table = 'feedbacks'
        verbose_name = 'Fikr va baholash'
        verbose_name_plural = 'Fikr va baholashlar'
        ordering = ['-created_at']

    def __str__(self):
        rating_str = f"{self.rating} yulduz" if self.rating else "Baholanmagan"
        return f"{self.user.first_name} - {rating_str}"

    @classmethod
    def get_average_rating(cls):
        """
        Barcha foydalanuvchilar o'rtacha bahosini qaytaradi.
        Har bir foydalanuvchining o'rtacha bahosi hisoblanadi, keyin umumiy o'rtacha topiladi.
        """
        from django.db.models import Avg

        # Har bir foydalanuvchining o'rtacha bahosi
        user_avg_ratings = cls.objects.filter(
            rating__isnull=False
        ).values('user').annotate(
            avg_rating=Avg('rating')
        )

        if not user_avg_ratings:
            return 0.0, 0

        # Umumiy o'rtacha
        total_avg = sum(item['avg_rating'] for item in user_avg_ratings) / len(user_avg_ratings)
        user_count = len(user_avg_ratings)

        return round(total_avg, 1), user_count

    @classmethod
    def get_user_average_rating(cls, user_id):
        """
        Berilgan foydalanuvchining o'rtacha bahosini qaytaradi.
        """
        from django.db.models import Avg

        result = cls.objects.filter(
            user__user_id=user_id,
            rating__isnull=False
        ).aggregate(avg_rating=Avg('rating'))

        return round(result['avg_rating'], 1) if result['avg_rating'] else None

    @classmethod
    def get_rating_stats(cls):
        """
        AppStore/PlayMarket o'xshash statistika qaytaradi.
        
        Returns:
            dict: {
                'total_votes': int,           # Jami ovoz berganlar
                'average_rating': float,      # O'rtacha reyting
                'by_rating': dict,            # Har bir yulduz uchun soni {1: x, 2: y, 3: z, 4: w, 5: v}
                'liked_count': int,           # Yoqganlar (4-5 yulduz)
                'disliked_count': int,        # Yoqmaganlar (1-2 yulduz)
                'neutral_count': int,        # Neytral (3 yulduz)
            }
        """
        from django.db.models import Count, Avg

        # Faqat baholangan fikrlarni olish
        rated_feedbacks = cls.objects.filter(rating__isnull=False, is_suggestion_only=False)

        # Jami ovoz
        total_votes = rated_feedbacks.count()

        if total_votes == 0:
            return {
                'total_votes': 0,
                'average_rating': 0.0,
                'by_rating': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                'liked_count': 0,
                'disliked_count': 0,
                'neutral_count': 0,
            }

        # O'rtacha reyting
        avg_result = rated_feedbacks.aggregate(avg_rating=Avg('rating'))
        average_rating = round(avg_result['avg_rating'], 1) if avg_result['avg_rating'] else 0.0

        # Har bir yulduz uchun soni
        rating_counts = {}
        for i in range(1, 6):
            count = rated_feedbacks.filter(rating=i).count()
            rating_counts[i] = count

        # Yoqganlar (4-5 yulduz), yoqmaganlar (1-2 yulduz), neytral (3 yulduz)
        liked_count = rating_counts[4] + rating_counts[5]
        disliked_count = rating_counts[1] + rating_counts[2]
        neutral_count = rating_counts[3]

        return {
            'total_votes': total_votes,
            'average_rating': average_rating,
            'by_rating': rating_counts,
            'liked_count': liked_count,
            'disliked_count': disliked_count,
            'neutral_count': neutral_count,
        }

    @classmethod
    def get_bio_text(cls):
        """
        Bot bio uchun matn generatsiya qiladi.
        AppStore/PlayMarket o'xshash formatda.
        """
        stats = cls.get_rating_stats()
        
        if stats['total_votes'] == 0:
            return "⭐️ Hali baholar yo'q"
        
        # Yulduzchalar
        stars = '⭐' * int(round(stats['average_rating']))
        
        # Matn
        bio = f"{stars} {stats['average_rating']} ({stats['total_votes']} ta ovoz)"
        
        return bio
