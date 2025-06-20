<?php

require_once __DIR__ . '/db.php';

error_reporting(E_ALL ^ E_WARNING);

spl_autoload_register(function ($class_name) {
    $filename = "core/$class_name.php";
    if (file_exists($filename)) {
        require_once($filename);
    }

    $filename = "handlers/$class_name.php";
    if (file_exists($filename)) {
        require_once($filename);
    }
});
