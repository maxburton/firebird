<html>
<head>

<link href="https://fonts.googleapis.com/css?family=Nunito" rel="stylesheet">
<style>
body{
	font-size: 20;
	font-family: 'Nunito', sans-serif;
}
</style>

<?php
	$url = $_POST["url"];
	$email = $_POST["email"];
	$password = $_POST["password"];
	
	if($password == 'XR,W=R&N7o3q_@QuWU!vfAbU'){
		$command = "cd /var/tools/firebird ; sudo -u ubuntu ./xvfb-run-safe python3 ./firebird.py ".$url." ".$email." '".$password."'";
		shell_exec($command);
		echo "The scraper has finished running. You should receive an email with the results shortly.";
	}else{
		echo "Incorrect password";
	}
?>


</head>

<body>
<br><br>
<a href="../firebird">Click here to go back</a>
</body>
</html>