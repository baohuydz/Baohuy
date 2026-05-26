<?php

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

$link = isset($_GET['link']) ? trim($_GET['link']) : '';

if(empty($link)){
    echo json_encode([
        "status"=>"error",
        "msg"=>"Thiếu link TikTok"
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

if(strpos($link,'tiktok.com') === false){
    echo json_encode([
        "status"=>"error",
        "msg"=>"Link TikTok không hợp lệ"
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

/*
 Token LeoFame
 Nếu hết hạn chỉ cần thay
*/
$token='5d01ce40835246daa138f6ee4cc0b03e';

$quantity=100;

$postData=http_build_query([
    'token'=>$token,
    'timezone_offset'=>'Asia/Saigon',
    'timezone_offset_2'=>'abcd',
    'free_link'=>$link,
    'quantity'=>$quantity
]);

$ch=curl_init();

curl_setopt_array($ch,[

    CURLOPT_URL=>'https://leofame.com/free-tiktok-likes?api=1',

    CURLOPT_POST=>true,

    CURLOPT_POSTFIELDS=>$postData,

    CURLOPT_RETURNTRANSFER=>true,

    CURLOPT_FOLLOWLOCATION=>true,

    CURLOPT_SSL_VERIFYPEER=>false,

    CURLOPT_ENCODING=>'',

    CURLOPT_TIMEOUT=>30,

    CURLOPT_USERAGENT=>
    'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/139 Mobile Safari/537.36',

    CURLOPT_HTTPHEADER=>[
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: https://leofame.com',
        'Referer: https://leofame.com/free-tiktok-likes'
    ],

    CURLOPT_COOKIE=>"token=".$token
]);

$response=curl_exec($ch);

$error=curl_error($ch);

$httpCode=curl_getinfo($ch,CURLINFO_HTTP_CODE);

curl_close($ch);

if($error){

    echo json_encode([
        "status"=>"error",
        "msg"=>"Lỗi CURL",
        "error"=>$error
    ],JSON_UNESCAPED_UNICODE);

    exit;
}

if($httpCode!=200){

    echo json_encode([
        "status"=>"error",
        "msg"=>"Không kết nối được",
        "http"=>$httpCode,
        "response"=>$response
    ],JSON_UNESCAPED_UNICODE);

    exit;
}

$success=
strpos($response,'success')!==false ||
strpos($response,'added')!==false ||
strpos($response,'buff')!==false;

if($success){

    echo json_encode([

        "status"=>"success",

        "msg"=>"Đã gửi buff thành công",

        "link"=>$link,

        "quantity"=>$quantity,

        "raw"=>$response

    ],JSON_UNESCAPED_UNICODE);

}else{

    echo json_encode([

        "status"=>"cooldown",

        "msg"=>"Link đã dùng hoặc đang giới hạn",

        "raw"=>$response

    ],JSON_UNESCAPED_UNICODE);

}
?>
