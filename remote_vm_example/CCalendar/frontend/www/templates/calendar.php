<!doctype html>
<html lang="en" class="h-100">

<head>
	<title>CCalendar</title>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
	<link href="https://fonts.googleapis.com/css?family=Lato:300,400,700&display=swap" rel="stylesheet">
	<link rel="stylesheet" href="/static/css/style.css">
</head>

<body class="h-100 d-flex flex-column">
	<section class="flex-grow-1 d-flex align-items-center justify-content-center pb-5">
		<div class="container w-100">
			<div class="row justify-content-center">
				<div class="col-md-6 text-center mb-5">
					<h1>CCalendar</h1>
					<h3>Welcome back, <?= $this->username ?></h3>
					<div>
						<button id="logout" class="btn btn-sm btn-secondary">Logout</button>
					</div>
				</div>
			</div>
			<div class="row">
				<div class="col-md-12">
					<div class="content w-100">
						<div class="calendar-container">
							<div class="calendar">
								<div class="year-header">
									<span class="left-button" id="prev"> </span>
									<span class="year" id="label"></span>
									<span class="right-button" id="next"> </span>
								</div>
								<table class="months-table w-100">
									<tbody>
										<tr class="months-row">
											<td class="month">Jan</td>
											<td class="month">Feb</td>
											<td class="month">Mar</td>
											<td class="month">Apr</td>
											<td class="month">May</td>
											<td class="month">Jun</td>
											<td class="month">Jul</td>
											<td class="month">Aug</td>
											<td class="month">Sep</td>
											<td class="month">Oct</td>
											<td class="month">Nov</td>
											<td class="month">Dec</td>
										</tr>
									</tbody>
								</table>

								<table class="days-table w-100">
									<td class="day">Sun</td>
									<td class="day">Mon</td>
									<td class="day">Tue</td>
									<td class="day">Wed</td>
									<td class="day">Thu</td>
									<td class="day">Fri</td>
									<td class="day">Sat</td>
								</table>
								<div class="frame">
									<table class="dates-table w-100">
										<tbody class="tbody">
										</tbody>
									</table>
								</div>
							</div>
						</div>
						<div class="events-container">
						</div>
						<div class="dialog" id="dialog">
							<h2 class="dialog-header" id="dialog-title">Add New Event</h2>
							<form class="form" id="form">
								<div class="form-container" align="center">
									<label class="form-label" for="title">Event title</label>
									<input class="input" type="text" id="event-title" name="title" maxlength="256">
									<label class="form-label" for="description">Event description</label>
									<input class="input" type="text" id="event-description" name="description" maxlength="256">
									<div id="form-invite-only">
										<label class="form-label" for="to">Send invite to</label>
										<input class="input" type="text" id="event-to" name="to" maxlength="32">
									</div>
									<input type="button" value="Cancel" class="button" id="cancel-button">
									<input type="button" value="OK" class="button button-white" id="ok-button">
								</div>
							</form>
							<p id="dialog-error">...</p>
						</div>
					</div>
					<div class="button-row">
						<button class="button mt-3 mx-2" id="new-event">New Event</button>
						<button class="button mt-3 mx-2" id="new-invite">New Invite</button>
					</div>
				</div>
			</div>
		</div>
	</section>
	<p id="license-notice">Based on <a href="https://colorlib.com/wp/template/calendar-04/" target="_blank">Calendar V04</a> &mdash; &copy; 2022 Rok Krivec &mdash; <a href="https://creativecommons.org/licenses/by/3.0/" target="_blank">CC-BY 3.0</a></p>
	<script src="/static/js/jquery.min.js"></script>
	<script src="/static/js/popper.js"></script>
	<script src="/static/js/bootstrap.min.js"></script>

	<script>
		var event_data = <?= json_encode($this->events) ?>
	</script>
	<script src="/static/js/main.js"></script>
</body>

</html>