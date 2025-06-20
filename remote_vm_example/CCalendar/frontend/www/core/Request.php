<?php

class Request
{
    public string $method;
    public string $path;

    public ?array $query;
    public ?array $form;

    public bool $is_json;
    public ?stdClass $json;
    public ?string $raw_body;

    public array $headers;
    public ?array $cookies;
    public ?string $user = null;

    public function __construct()
    {
        global $database;

        $this->method = $_SERVER['REQUEST_METHOD'];

        $full_path = 'http://' . $_SERVER['SERVER_NAME'] . $_SERVER['REQUEST_URI'];
        $parsed_path = parse_url($full_path);

        $this->path = $parsed_path['path'];
        if (isset($parsed_path['query']))
            parse_str($parsed_path['query'], $this->query);

        $this->headers = getallheaders();
        $this->raw_body = file_get_contents('php://input');

        $this->is_json = false;
        if (isset($this->headers['Content-Type']) && strtolower($this->headers['Content-Type']) === 'application/json') {
            try {
                $this->json = json_decode($this->raw_body);
                $this->is_json = true;
            } catch (JsonException $e) {
            }
        }

        $this->form = $_POST;
        $this->cookies = $_COOKIE;

        if (isset($this->cookies['user']) && isset($this->cookies['user_hash'])) {
            if (password_verify($this->cookies['user'] . getenv('CRYPT_SECRET'), $this->cookies['user_hash'])) {
                // check user is in db
                // you shouldn't be able to have a valid signed cookie for a non-existent user,
                // this is here just in case you for some reason decide to reset the db
                // this was mostly useful during testing
                // there is no intended vuln that allows you to craft a signed cookie, and honestly we are pretty sure
                // there is no unintended vuln here as well. please don't waste time here
                $stmt = $database->prepare('SELECT COUNT(*) FROM users WHERE username = ?');
                $stmt->execute([$this->cookies['user']]);
                if ($stmt->fetchColumn() === 1) {
                    $this->user = $this->cookies['user'];
                } else {
                    $this->clean_user_cookies();
                }
            } else {
                $this->clean_user_cookies();
            }
        }
    }

    private function clean_user_cookies()
    {
        unset($_COOKIE['user']);
        setcookie(
            name: 'user',
            value: '',
            expires_or_options: -1,
            path: '/'
        );

        unset($_COOKIE['user_hash']);
        setcookie(
            name: 'user_hash',
            value: '',
            expires_or_options: -1,
            path: '/'
        );
    }
}
