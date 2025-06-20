<?php

class Login extends Response
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

        $this->username = trim($request->form['username']);
        $this->password = trim($request->form['password']);
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
            $stmt = $database->prepare('SELECT password FROM users WHERE username = ?');
            $stmt->execute([$this->username]);
            $user = $stmt->fetch();

            if ($user && password_verify($this->password, $user->password)) {
                setcookie(
                    name: 'user',
                    value: $this->username,
                    path: '/'
                );
                setcookie(
                    name: 'user_hash',
                    value: crypt($this->username . getenv('CRYPT_SECRET'), '$5$rounds=1000$' . bin2hex(random_bytes(8)) . '$'),
                    path: '/'
                );

                header('Location: /');
            } else {
                $this->throw_error('wrong password');
            }
        } catch (PDOException $e) {
            $this->throw_error('error while logging in');
        }
    }
}
