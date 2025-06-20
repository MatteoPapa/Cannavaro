<?php

try {
	$database = new PDO("sqlite:/app/db/db.sqlite");
	$database->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_OBJ);

	$database->exec('CREATE TABLE IF NOT EXISTS users (
        username VARCHAR(32) PRIMARY KEY, 
        password VARCHAR(60)
    )');
} catch (PDOException $e) {
	print_r($e);
	die("Could not connect to the database");
}
