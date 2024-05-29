from django.db import models

class Redemption(models.Model):
    child = models.ForeignKey('Child', on_delete=models.CASCADE, verbose_name='Child')
    points_used = models.IntegerField(verbose_name='Points Used')
    date_redeemed = models.DateTimeField(auto_now_add=True, verbose_name='Date Redeemed')
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE, verbose_name='Shop')

    def __str__(self):
        return f'{self.child} redeemed {self.points_used} points at {self.shop} on {self.date_redeemed}'
