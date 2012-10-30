#coding: utf-8
from django.utils.translation import ugettext as _
from django.http import HttpResponse, Http404
from django.core.paginator import Paginator, InvalidPage, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.conf import settings
from django import shortcuts

from user.models import Account
from payment.models import PayOrder
from common.api.tenpay import gen_order, return_url, notify_url
from report.tools import render
from common.templatetags.currency import asmoney

# generate order
def tenpay_generate_order(request):
    if request.method == "POST":
        # get account info by dashboard user instead of openstack user, and raise 404 if no such account
        account = shortcuts.get_object_or_404(Account, id=request.ouser.account_id)
        
        data = request.POST
        total_fee = data['money']
        if total_fee not in ('100', '200', '500'):
            messages.error(request, _('You choose a wrong recharge amount, please choose again.'))
        else:
            total_fee = int(total_fee) * settings.RECHARGE_FEE_RATE # make 1 indicates 100 Fen
            sendsms = data.get('sendsms', False)
            bank_type = 'DEFAULT'
            goods_name = _('CloudOpen Recharge %s') % asmoney(total_fee)
            ret_data = dict()
            ret_data['total_fee'] = total_fee 
            ret_data['goods_name'] = goods_name
            ret_data['phone_no'] = account.cellphone
            ret_data['payment'] = 0
            request_url,all_parameters = gen_order(goods_name,str(total_fee),bank_type,sendsms,request)  # cause API only accept str :(
            return render('tenpay/order_info.html',{'requrl':request_url,'ret_data':ret_data,"all_parameters":all_parameters },request)
    
    username = request.session['user_name']
    all_orders = PayOrder.objects.filter(username=username).order_by('-order_date')
    
    page_size = 6
    after_range_num = 4
    before_range_num = 5
    try:
        page = int(request.GET.get('page',1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    paginator = Paginator(all_orders,page_size)
    try:
        orders = paginator.page(page)
    except(EmptyPage, InvalidPage, PageNotAnInteger):
        orders = paginator.page(1)
    if page >= after_range_num:
        page_range = paginator.page_range[page - after_range_num : page + before_range_num]
    else:
        page_range = paginator.page_range[0:int(page) + before_range_num]
    
    return render('tenpay/generate_order.html',{'show_recharge_form':True,'orders':orders,
                                                'page_range':page_range},request)


# search order
def tenpay_order_info(request,order_id):
    p = PayOrder.objects.get(trade_no=order_id)
    ret_order_info = dict()
    ret_order_info['goods_name'] = p.goods_name
    ret_order_info['order_date'] = p.order_date
    ret_order_info['trade_no'] = p.trade_no
    ret_order_info['total_fee'] = p.total_fee
    ret_order_info['payment_info'] = p.payment_info
    ret_order_info['requrl'] = p.requrl
    
    if request.is_ajax():
        return render('tenpay/order_info_ajax.html',{'ret_order_info':ret_order_info},request)
        
    return render('tenpay/order_info.html',{'ret_order_info':ret_order_info},request)

# for return url from tenpay
def tenpay_order_return(request):
    ret = return_url(request)
    if isinstance(ret,dict):
        return render('tenpay/order_info.html',{'payment_success':True},request)
    else:
        pass

# for notify url from tenpay
def tenpay_order_notify(request):
    ret = notify_url(request)
    if "success" == ret:
        return HttpResponse(ret)
    else:
        return HttpResponse("fail")



