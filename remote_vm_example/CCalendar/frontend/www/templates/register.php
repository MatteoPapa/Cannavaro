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
				</div>
			</div>
			<div class="row justify-content-center">
				<div class="col-md-6">
					<?php if (isset($this->error)) { ?>
						<div class="alert alert-danger" role="alert">
							<?= $this->error ?>
						</div>
					<?php } ?>

					<?php if (isset($this->success)) { ?>
						<div class="alert alert-success" role="alert">
							<?= $this->success ?>
						</div>
					<?php } ?>
					</form>
				</div>
			</div>
			<div class="row justify-content-center">
				<div class="col-md-6">
					<h2 class="heading-section text-center mt-4 mb-4">Register</h2>
					<form action="/register" method="POST" class="px-5 bg-light">
						<div class="form-group">
							<input type="text" class="form-control" name="username" placeholder="Username" required>
						</div>
						<div class="form-group">
							<input type="password" class="form-control" name="password" placeholder="Password" required>
						</div>

						<div class="form-group text-center">
							<input type="submit" value="Register" class="button">
						</div>
					</form>
				</div>
				<div class="col-md-6">
					<h2 class="heading-section text-center mt-4 mb-4">Login</h2>
					<form action="/login" method="POST" class="px-5 bg-light">
						<div class="form-group">
							<input type="text" class="form-control" name="username" placeholder="Username" required>
						</div>
						<div class="form-group">
							<input type="password" class="form-control" name="password" placeholder="Password" required>
						</div>

						<div class="form-group text-center">
							<input type="submit" value="Login" class="button">
						</div>
					</form>
				</div>
			</div>
		</div>
	</section>
	<p id="license-notice">Based on <a href="https://colorlib.com/wp/template/calendar-04/" target="_blank">Calendar V04</a> &mdash; &copy; 2022 Rok Krivec &mdash; <a href="https://creativecommons.org/licenses/by/3.0/" target="_blank">CC-BY 3.0</a></p>
	<script src="/static/js/jquery.min.js"></script>
	<script src="/static/js/popper.js"></script>
	<script src="/static/js/bootstrap.min.js"></script>
</body>

</html>