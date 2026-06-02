"""
Viloyat, Tuman modellari + geopy koordinata olish
"""
import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger("apps.regions")


class Region(models.Model):
    """Viloyat / Respublika"""
    name   = models.CharField(max_length=200, verbose_name="Nomi")
    

    class Meta:
        db_table     = "regions"
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"
        ordering = ["name"]

    def __str__(self):
        return self.name


class District(models.Model):
    """
    Tuman / Shahar.
    Admin tuman qo'shganda JSON dan nom yoki terib tanlaydi,
    geopy orqali koordinatalar avtomatik olinadi.
    """
    region        = models.ForeignKey(
        Region, on_delete=models.CASCADE,
        related_name="districts", verbose_name="Viloyat"
    )
    name          = models.CharField(max_length=200, verbose_name="Nomi")
    

    # Geopy bilan olingan koordinatalar
    latitude      = models.FloatField(null=True, blank=True, verbose_name="Kenglik")
    longitude     = models.FloatField(null=True, blank=True, verbose_name="Uzunlik")
    geo_address   = models.TextField(blank=True, verbose_name="Geopy manzil")
    geo_fetched   = models.BooleanField(default=False, verbose_name="Geo olindi")

    # Xizmat mavjudligi va narxi
    is_active         = models.BooleanField(default=False, verbose_name="Xizmat mavjud")
    delivery_price    = models.IntegerField(default=0, verbose_name="Yetkazish narxi (so'm)")

    class Meta:
        db_table     = "districts"
        verbose_name = "Tuman"
        verbose_name_plural = "Tumanlar"
        ordering = ["region__name", "name"]
        unique_together = [("region", "name")]
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.region.name})"

    def fetch_coordinates(self, force=False):
        """
        geopy Nominatim orqali koordinatalarni olish.
        force=True bo'lsa qayta oladi.
        """
        if self.geo_fetched and not force:
            return True

        try:
            from geopy.geocoders import Nominatim
            from geopy.extra.rate_limiter import RateLimiter

            geolocator = Nominatim(user_agent=settings.GEOPY_USER_AGENT)
            geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

            # Qidiruv so'rovi: "Tuman nomi, Uzbekistan"
            query = f"{self.name}, Uzbekistan"
            location = geocode(query, language="uz", timeout=10)

            if location:
                self.latitude   = location.latitude
                self.longitude  = location.longitude
                self.geo_address = location.address
                self.geo_fetched = True
                self.save(update_fields=["latitude", "longitude", "geo_address", "geo_fetched"])
                logger.info("Coordinates fetched: %s → %.4f, %.4f", self.name, self.latitude, self.longitude)
                return True
            logger.warning("Coordinates not found for: %s", self.name)
            return False

        except Exception as e:
            logger.error("Geopy error for %s: %s", self.name, e)
            return False
        return False

    @property
    def coords(self):
        """(lat, lon) tuple yoki None"""
        if self.latitude and self.longitude:
            return (self.latitude, self.longitude)
        return None


class BotSetting(models.Model):
    """
    Bot sozlamalari — key/value store.
    Admin panel orqali o'zgartiriladi.
    """
    key   = models.CharField(max_length=100, unique=True, verbose_name="Kalit")
    value = models.TextField(blank=True, verbose_name="Qiymat")

    class Meta:
        db_table     = "bot_settings"
        verbose_name = "Bot sozlamasi"
        verbose_name_plural = "Bot sozlamalari"

    def __str__(self):
        return f"{self.key} = {self.value[:50]}"

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value):
        obj, _ = cls.objects.update_or_create(
            key=key, defaults={"value": str(value)}
        )
        return obj