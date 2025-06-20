<?php

class Register extends Response
{
    private string $username;
    private string $password;

    function __construct(Request $request)
    {
        if ($request->method === 'GET') {
            header('Location: /');
            die;
        }

        if ($request->method !== 'POST') {
            http_response_code(405);
            die;
        }

        if (!isset($request->form['username']) || !isset($request->form['password']))
            $this->throw_error('username and password are required');

        if (!is_string($request->form['username']) || !is_string($request->form['password']))
            $this->throw_error('username and password must be strings');

        if (strlen(trim($request->form['username'])) < 2 || strlen(trim($request->form['password'])) < 2)
            $this->throw_error('username and password must be at least 2-chars long');

        if (preg_match('/^.*[^a-zA-Z0-9].*$/', $request->form['username']))
            $this->throw_error('username cannot contain special chars');

        $this->username = trim($request->form['username']);
        $this->password = password_hash(trim($request->form['password']), PASSWORD_BCRYPT, ['cost' => 4]);
    }

    private function throw_error(string $details = '')
    {
        $template = new Template('register.php', ['error' => $details]);
        die($template->render());
    }

    function render()
    {
        global $database;

        try {
            $stmt = $database->prepare('INSERT INTO users (username, password) VALUES (?, ?)');
            $res = $stmt->execute([$this->username, $this->password]);

            if ($res) {
                $template = new Template('register.php', ['success' => 'user created successfully']);
                die($template->render());
            } else {
                $this->throw_error('error while registrating the user');
            }
        } catch (PDOException $e) {
            if ($e->getCode() === '23000') {
                $this->throw_error('user already exists');
            }
        }
    }
}
