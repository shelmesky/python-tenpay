from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

class PayOrder(models.Model):
    username = models.CharField(max_length=128, db_index=True, verbose_name=_('Username'))
    user_id = models.CharField(blank=True, null=True, max_length=64, verbose_name=_('UserID'))
    tenant_id  = models.CharField(blank=True, null=True, max_length=64, verbose_name=_('TenantID '))
    goods_name = models.CharField(max_length=256, verbose_name=_('Goods Name'))
    order_date = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Time'))
    trade_no = models.CharField(max_length=128, unique=True, verbose_name=_('Out Trade Number'))
    total_fee = models.IntegerField(max_length=64, verbose_name=_('Total Fee'))
    transaction_id = models.CharField(blank=True, null=True, max_length=128, verbose_name=_('Transaction ID'))
    trade_state = models.IntegerField(blank=True, null=True, max_length=1, verbose_name=_('Trade State'))
    trade_mode = models.IntegerField(blank=True, null=True, max_length=1, verbose_name=_('Trade Mode'))
    pay_info = models.CharField(blank=True, null=True, max_length = 128, verbose_name=_('Pay Info'))
    ret_code = models.CharField(blank=True, null=True, max_length = 8, verbose_name=_('Return Info'))
    ret_msg = models.CharField(blank=True, null=True, max_length = 256, verbose_name=_('Return Message'))
    send_sms = models.BooleanField(verbose_name = _('Send Sms To User'))
    requrl = models.CharField(blank=True, null=True, max_length=1024,verbose_name = _('Payment Reques URL'))
    
    payment_choice = (
        (0,'NEW_ORDER'),
        (1,'PAYMENT'),
        (2,'MONEY_RECEIVED'),
    )
    payment_info = models.CharField(blank=True, null=True, max_length=8,choices=payment_choice,verbose_name=_('Payment Info'))
    
    def __unicode__(self):
        return smart_unicode('%s [%s] [%s]' % (self.username, self.order_date, self.goods_name))
    
    class Meta:
        verbose_name = _('PayOrder')
        verbose_name_plural = _('PayOrder')
        ordering = ['-order_date']