<?php

class Calendar extends Response
{
    private Request $request;
    /** @var stdClass[] $events */
    private array $events;

    function __construct(Request $request)
    {
        $this->request = $request;

        $res = json_decode(file_get_contents('http://api/events/' . $request->user));

        if ($res === null || !$res->success) {
            die((new Template('register.php', ['error' => 'cannot retrieve user events']))->render());
        }

        $this->events = [];
        foreach ($res->events as $event) {
            $this->events[] = [
                'id' => $event->id,
                'title' => $event->title,
                'description' => $event->description,
                'year' => intval(explode('-', $event->date)[0]),
                'month' => intval(explode('-', $event->date)[1]),
                'day' => intval(explode('-', $event->date)[2]),
            ];
        }
    }

    function render()
    {
        die((new Template('calendar.php', ['username' => $this->request->user, 'events' => ['events' => $this->events]]))->render());
    }
}
