<?php

require_once './core/init.php';

$request = new Request();
/** @var Response $response */
$response;

if (str_starts_with($request->path, '/static/')) {
    $response = new StaticFile($request);
} else if ($request->path === '/') {
    if ($request->user) {
        $response = new Calendar($request);
    } else {
        $response = new Template('register.php');
    }
} else if ($request->path === '/register') {
    $response = new Register($request);
} else if ($request->path === '/login') {
    $response = new Login($request);
}

if (!isset($response)) {
    http_response_code(404);
    return;
}

$response->render();
