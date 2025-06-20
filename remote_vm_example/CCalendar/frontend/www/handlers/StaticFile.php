<?php

class StaticFile extends Response
{
    private Request $request;
    private string $mime_type;

    function __construct($request)
    {
        $this->request = $request;

        if (str_contains($request->path, '.php') || str_contains($request->path, '..')) {
            http_response_code(403);
            die;
        }

        if (str_ends_with($this->request->path, '.html')) {
            $this->mime_type = 'text/html';
        } else if (str_ends_with($this->request->path, '.js')) {
            $this->mime_type = 'text/javascript';
        } else if (str_ends_with($this->request->path, '.css')) {
            $this->mime_type = 'text/css';
        } else {
            $this->mime_type = 'text/plain';
        }
    }

    function render()
    {
        try {
            $content = file_get_contents(substr($this->request->path, 8));
            header("Content-Type: $this->mime_type");

            die($content !== false ? $content : throw new Exception());
        } catch (Exception $_) {
            http_response_code(404);
            die;
        }
    }
}
