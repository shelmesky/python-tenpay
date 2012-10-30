#coding: utf-8
import hashlib
import urllib
from xml.dom import minidom
import pycurl
from cStringIO import StringIO
from random import randint
import datetime

from django.http import HttpResponseRedirect, HttpResponse 
from django.conf import settings
from django.core.urlresolvers import reverse

from common import LOG

from payment.models import PayOrder
from user.models import Account
from tenant.models import Tenant
from tenant.utils import send_balance_increase_sms

partner = settings.TENPAY_PARTNER
key = settings.TENPAY_KEY
activate_host = settings.ACTIVATE_HOST
payment_order_gateurl  = settings.TENPAY_PAYMENT_URL
recharge_exchange_rate = settings.RECHARGE_EXCHANGE_RATE


class ClientResponseHandler(object):
    def __init__(self):
        self._ClientResponseHandler()
    
    def _ClientResponseHandler(self):
        self.key = ""
        self.parameters = dict()
        self.debugInfo = ""
        self.content = ""
        
    def getKey(self):
        return self.key
    
    def setKey(self,key):
        self.key = key
    
    def setContent(self,content):
        content = content.replace('<?xml version="1.0" encoding="GBK"?>','<?xml version="1.0" encoding="utf-8"?>')
        doc = minidom.parseString(content)
        dict1 = dict()
        list1 = list()
        
        root = doc.firstChild
        
        for n in root.childNodes:
            for i in n.childNodes:
                dict1[i.parentNode.nodeName] = i.nodeValue

        for n in root.childNodes:
            if "text" not in n.nodeName:
                list1.append(n.nodeName)

        final_dict = {}.fromkeys(list1)

        for item in dict1:
            final_dict[item] = dict1[item]
        
        for k,v in final_dict.items():
            self.setParameter(k,v)
    
    def getContent(self):
        return self.content
    
    def getParameter(self,parameter):
        return self.parameters[parameter]
    
    def setParameter(self,parameter,parameterValue):
        self.parameters[parameter] = parameterValue if parameterValue == None else parameterValue.encode('utf-8')
    
    def getALLParameters(self):
        return self.parameters
    
    def isTenpaySign(self):
        signPars = ''
        parms = self.parameters.keys()
        parms.sort()
        my_parms = [{key:self.parameters[key]} for key in parms]
        for x in my_parms:
            for k in x:
                if x[k] and k != 'sign':
                    signPars += k + '=' + x[k] + '&'
        signPars += 'key=' + self.key
        sign = hashlib.md5(signPars.encode('utf-8')).hexdigest().lower()
        tenpaySign = self.getParameter("sign").lower()
        
        self._setDebugInfo(signPars + ' => sign:' + sign +
                           "tenpaySign: " + self.getParameter("sign"))
        
        return sign == tenpaySign
    
    
    def getDebugInfo(self):
        return self.debugInfo
    
    def getXmlEncode(self,xml):
        pass
    
    def _setDebugInfo(self,debugInfo):
        self.debugInfo = debugInfo



class TenpayHttpClient(object):
    def __init__(self):
        self.TenpayHttpClient()
    
    def TenpayHttpClient(self):
        """
            init some variables
        """
        self.reqContent = ""
        self.resContent = ""
        self.method = "POST"
        
        self.certFile = ""
        self.certPasswd = ""
        self.certType = "PEM"
        
        self.caFile = ""
        
        self.errInfo = ""
        
        self.timeOut = 120
        
        self.responseCode = 0
    
    def setReqContent(self,reqContent):
        self.reqContent = reqContent
    
    def getResContent(self):
        return self.resContent
    
    def setMethod(self,method):
        self.method = method
    
    def getErrInfo(self):
        return self.errInfo

    def setCertInfo(self,certFile,certPasswd,certType="PEM"):
        self.certFile = certFile
        self.certPasswd = certPasswd
        self.certType = certType
    
    def setCaInfo(self,caFile):
        self.caFile = caFile
    
    def setTimeOut(self,timeOut):
        self.timeOut = timeOut
    
    def call(self):
        """
            perform curl call
        """
        curl = pycurl.Curl()
        
        # set timeout for curl
        curl.setopt(pycurl.TIMEOUT,self.timeOut)
        
        # verify ssl certificate for host
        curl.setopt(pycurl.SSL_VERIFYHOST,1)
        
        buff = StringIO()
        
        # set output function for pycurl
        curl.setopt(pycurl.WRITEFUNCTION,buff.write)
        
        arr = self.reqContent.split('?')
        # if post set postfields
        if len(arr) >=2 and self.method == "post":
            curl.setopt(pycurl.POST,1)
            curl.setopt(pycurl.URL,arr[0])
            curl.setopt(pycurl.POSTFIELDS,arr[1])
        else:
            curl.setopt(pycurl.URL,self.reqContent)
        
        # if has ca will verify ssl certificate host
        if self.caFile:
            curl.setopt(pycurl.SSL_VERIFYHOST,1)
            curl.setopt(pycurl.CAINFO,self.caFile)
        else:
            curl.setopt(pycurl.SSL_VERIFYHOST,0)
        
        # perform curl request and get value from write buff(stringIO)
        curl.perform()
        res = buff.getvalue()
        self.responseCode =  curl.getinfo(pycurl.HTTP_CODE)
        
        # if curl performed failed, get error information
        if not res:
            self.errInfo = "call http err :" + curl.errstr()
            curl.close()
            return False
        # else if response code not equal 200
        elif self.responseCode != 200:
            self.errInfo = "call http err httpcode=" + str(self.responseCode)
            curl.close()
            return False
        
        curl.close()
        self.resContent = res
        
        return True


    def getResponseCode(self):
        return self.responseCode()



class RequestHandler(object):
    def __init__(self):
        self.RequestHandler()
    
    def RequestHandler(self):
        self.gateUrl = 'https://www.tenpay.com/cgi-bin/v1.0/service_gate.cgi'
        self.key = ''
        self.parameters = dict()
        self.debuginfo = ''
    
    def init(self):
        pass
    
    def getGateURL(self):
        return self.gateUrl
    
    def setGateURL(self,gateUrl):
        self.gateUrl = gateUrl
    
    def getKey(self):
        return self.key
    
    def setKey(self,key):
        self.key = key
    
    def getParameter(self,parameter):
        return self.parameters[parameter]
    
    def setParameter(self,parameter,parameterValue):
        self.parameters[parameter] = parameterValue if parameterValue == None else parameterValue.encode('utf-8')
    
    def getAllParameters(self):
        return self.parameters
    
    def getRequestURL(self):
        self.createSign()
        
        
        parms = self.parameters.items()
        parms.sort()
        
        reqPar = urllib.urlencode(parms)
        
        requestURL = self.getGateURL() + '?' + reqPar
        
        return requestURL
    
    def getDebugInfo(self):
        return self.debuginfo
    
    def doSend(self):
        return HttpResponseRedirect(self.getRequestURL())
    
    def createSign(self):
        signPars = ''
        parms = self.parameters.keys()
        parms.sort()
        my_parms = [{key:self.parameters[key]} for key in parms]
        for x in my_parms:
            for k in x:
                if x[k] != '' and k != 'sign':
                    signPars += k + '=' + x[k] + '&'
        signPars += 'key=' + self.key
        sign = hashlib.md5(signPars).hexdigest().lower()
        self.setParameter('sign',sign)
        
        self._setDebugInfo(signPars + ' => sign:' + sign)
    
    def _setDebugInfo(self,debugInfo):
        self.debuginfo=debugInfo



class ResponseHandler(object):
    def __init__(self,request):
        self.request = request
        self.ResponseHandler()
    
    def ResponseHandler(self):
        self.key = ""
        self.parameters = dict()
        self.debugInfo = ""
        
        #GET
        gets = self.request.GET
        for k in gets:
            self.parameters[k] = gets[k]
        
        #POST
        posts = self.request.POST
        for k in posts:
            self.parameters[k] = posts[k]
    
    def getKey(self):
        return self.key
    
    def setKey(self,key):
        self.key = key

    def getParameter(self,parameter):
        return self.parameters[parameter]

    def setParameter(self,parameter,parameterValue):
        self.parameters[parameter] = parameterValue if parameterValue == None else parameterValue.encode('utf-8')
    
    def getALLParameters(self):
        return self.parameters

    def isTenpaySign(self):
        signPars = ''
        parms = self.parameters.keys()
        parms.sort()
        my_parms = [{key:self.parameters[key]} for key in parms]
        for x in my_parms:
            for k in x:
                if x[k] != '' and k != 'sign':
                    signPars += k + '=' + x[k] + '&'
        signPars += 'key=' + self.key
        sign = hashlib.md5(signPars.encode('utf-8')).hexdigest().lower()
        
        tenpaySign = self.getParameter("sign").lower()
        
        self._setDebugInfo(signPars + "<br />" +" => sign: " + sign + "<br />" +\
                           "tenpaySign: " + self.getParameter("sign"))
        
        return ( sign == tenpaySign )
    
    def getDebugInfo(self):
        return self.debugInfo
    
    def doShow(self,show_url):
        strHtml = """
        <html><head><meta name="TENCENT_ONLINE_PAYMENT" content="China TENCENT">
        <script language="javascript">
        window.location.href="%s"
        </script>
        </head><body></body></html>
        """ % show_url
        
        return HttpResponse(strHtml)

    def _setDebugInfo(self,debugInfo):
        self.debugInfo = debugInfo

def gen_order(goods_name,total_fee,bank_type,send_sms,request):
    randNum = randint(1000,9999)
    out_trade_no = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(randNum)
    
    reqHandler = RequestHandler()
    reqHandler.init()
    reqHandler.setKey(key)
    reqHandler.setGateURL(payment_order_gateurl)
    reqHandler.setParameter("total_fee",total_fee)
    reqHandler.setParameter("spbill_create_ip",request.META["REMOTE_ADDR"])
    reqHandler.setParameter("return_url",activate_host + reverse('order-return'))
    reqHandler.setParameter("partner",partner)
    reqHandler.setParameter("out_trade_no",out_trade_no)
    reqHandler.setParameter("notify_url",activate_host + reverse('order-notify'))
    reqHandler.setParameter("body",goods_name)
    reqHandler.setParameter("bank_type",bank_type)
    reqHandler.setParameter("fee_type","1")
    
    #可选参数
    reqHandler.setParameter("sign_type","MD5")
    reqHandler.setParameter("service_version","1.0")
    reqHandler.setParameter("input_charset","utf-8")
    reqHandler.setParameter("sign_key_index","1")
    
    #业务可选参数
    reqHandler.setParameter("attach","")
    reqHandler.setParameter("product_fee","")
    reqHandler.setParameter("transport_fee","")
    reqHandler.setParameter("time_start",datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
    reqHandler.setParameter("time_expire","")
    
    reqHandler.setParameter("buyer_id","")
    reqHandler.setParameter("goods_tag","")
    
    reqUrl = reqHandler.getRequestURL()
    allParameter = reqHandler.getAllParameters()
    
    pay_order = PayOrder(
        username = request.session['user_name'],
        user_id = request.session['user_id'],
        tenant_id = request.session['tenant_id'],
        #username = 'lmh2506@163.com',
        #user_id = '123',
        #tenant_id = '123',
        goods_name = goods_name,
        trade_no = out_trade_no,
        total_fee = total_fee,
        send_sms = send_sms,
        payment_info = 0,
        requrl = reqUrl
    )
    pay_order.save()
    
    return reqUrl,allParameter

def return_url(request):
    #得到财付通的payreturn
    resHandler = ResponseHandler(request)
    resHandler.setKey(key)
    
    #验证财付通返回的URL中的信息
    if resHandler.isTenpaySign():
        notify_id = resHandler.getParameter("notify_id")
        out_trade_no = resHandler.getParameter("out_trade_no")
        transaction_id = resHandler.getParameter("transaction_id")
        total_fee = resHandler.getParameter("total_fee")
        discount = resHandler.getParameter("discount")
        trade_state = resHandler.getParameter("trade_state")
        trade_mode = resHandler.getParameter("trade_mode")
        
        #验证返回的URL中的trade_state 和 trade_mode
        if trade_state == "0" and trade_mode == "1":
            # 此处记录不可靠
            #p = PayOrder.objects.get(trade_no=out_trade_no)
            #p.transaction_id = transaction_id
            #p.trade_state = trade_state
            #p.trade_mode = trade_mode
            #p.payment_info = 1
            #p.save()
            return resHandler.getALLParameters()
        else:
            return False
    
    #return resHandler.getDebugInfo()

def notify_url(request):
    #首先得到财付通的发来的GET请求
    resHandler = ResponseHandler(request)
    resHandler.setKey(key)
    
    if resHandler.isTenpaySign():
        #得到notify_id
        notify_id = resHandler.getParameter("notify_id")
        LOG.debug("got notify_id: %s" % notify_id) 
        
        queryReq = RequestHandler()
        queryReq.init()
        queryReq.setKey(key)
        queryReq.setGateURL("https://gw.tenpay.com/gateway/verifynotifyid.xml")
        queryReq.setParameter("partner",partner)
        queryReq.setParameter("notify_id",notify_id)
        
        httpClient = TenpayHttpClient()
        httpClient.setTimeOut(5)
        httpClient.setReqContent(queryReq.getRequestURL())
        LOG.debug("queryReq.getRequestURL() : %s" % queryReq.getRequestURL()) 
        
        #根据得到的notify_id再次到财付通查询验证订单消息
        if httpClient.call():
            #负责解析httpClient从财付通得到的xml格式中的内容
            queryRes = ClientResponseHandler()
            #加载由httpClient返回的内容
            queryRes.setContent(httpClient.getResContent())
            LOG.debug("queryRes.getALLParameters(): %s" % queryRes.getALLParameters())
            LOG.debug("httpClient.getResContent() : %s" % httpClient.getResContent()) 
            queryRes.setKey(key)
            
            if queryRes.isTenpaySign() and queryRes.getParameter("retcode") == "0" and queryRes.getParameter("trade_state") == "0" and queryRes.getParameter("trade_mode") == "1":
                out_trade_no = queryRes.getParameter("out_trade_no")
                transaction_id = queryRes.getParameter("transaction_id")
                trade_state = queryRes.getParameter("trade_state")
                trade_mode = queryRes.getParameter("trade_mode")
                
                total_fee = queryRes.getParameter("total_fee")
                
                discount = queryRes.getParameter("discount")
                
                #开始处理业务
                #注意验证订单不要重复
                #注意判断返回金额
                p = PayOrder.objects.get(trade_no=out_trade_no)
                if p.total_fee == int(total_fee) and p.payment_info != '2':
                    p.transaction_id = transaction_id
                    p.trade_state = trade_state
                    p.trade_mode = trade_mode
                    p.ret_code = queryRes.getParameter("retcode")
                    p.ret_msg = queryRes.getParameter("retmsg")
                    p.payment_info = 2
                    p.save()
                    try:
                        tenant_id = p.tenant_id
                        tenant = Tenant.objects.get(tenant_id=tenant_id)
                        increase = (int(total_fee) * int(recharge_exchange_rate))
                        tenant.balance += increase
                        tenant.save()
                        if p.send_sms:
                            send_balance_increase_sms(p, tenant, increase)
                    except Exception,e:
                        LOG.error(e)
                        raise e
                else:
                    pass
                
                #处理完毕
                
                LOG.debug("Trade completed processed: out_trade_no: %s\n total_fee:%s\n transaction_id:%s\n" % (out_trade_no,total_fee,transaction_id))
                
                return "success"
            
            else:
                LOG.debug("Check sign failed or trade err: trade_state=%s\n retcode=%s\n retmsg=%s\n" % (queryRes.getParameter("trade_state"),
                                                                                                         queryRes.getParameter("ret_code"),
                                                                                                         queryRes.getParameter("retmsg")))
                return "fail"
            
    else:
        LOG.debug("Communication with tenpay failed: responsecode=%s\n error_info=%s\n" % (httpClient.getResponseCode(),httpClient.getErrInfo()))
        return "fail"
    
    return "fail"


