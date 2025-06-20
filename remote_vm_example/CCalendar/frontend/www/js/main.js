// The service has no intended client-side vulnerabilities.
// Even if there were XSS or similar vulns present, the checker does not use a
// browser. You are free to look at this code in order to understand how the
// service works, but don't waste time looking for vulns here.

// Most of the code comes from the bootstrap calendar template at:
// https://colorlib.com/wp/template/calendar-04/
// Additional functionality has been hacked together on top of it. The code is
// not really meant to be easy to read nor efficient.

(function ($) {
	'use strict';

	// Setup the calendar with the current date
	$(document).ready(function () {
		var date = new Date();
		var today = date.getDate();

		// Set click handlers for DOM elements
		$('.right-button').click({ date: date }, handler_next_year);
		$('.left-button').click({ date: date }, handler_prev_year);
		$('.month').click({ date: date }, handler_month_click);
		$('#new-event').click({ date: date }, handler_new_event);
		$('#new-invite').click({ date: date }, handler_new_invite);
		$('#logout').click(logout_click);

		// Set current month as active
		$('.months-row').children().eq(date.getMonth()).addClass('active-month');
		init_calendar(date);

		var events = check_events(today, date.getMonth() + 1, date.getFullYear());
		show_events(events, months[date.getMonth()], today, date.getFullYear());
	});

	// Initialize the calendar by appending the HTML dates
	function init_calendar(date) {
		$('.tbody').empty();
		$('.events-container').empty();
		var calendar_days = $('.tbody');
		var month = date.getMonth();
		var year = date.getFullYear();
		var day_count = days_in_month(month, year);
		var row = $("<tr class='table-row'></tr>");
		var today = date.getDate();
		// Set date to 1 to find the first day of the month
		date.setDate(1);
		var first_day = date.getDay();
		// 35+firstDay is the number of date elements to be added to the dates table
		// 35 is from (7 days in a week) * (up to 5 rows of dates in a month)
		for (var i = 0; i < 35 + first_day; i++) {
			// Since some of the elements will be blank,
			// need to calculate actual date from index
			var day = i - first_day + 1;
			// If it is a sunday, make a new row
			if (i % 7 === 0) {
				calendar_days.append(row);
				row = $("<tr class='table-row'></tr>");
			}
			// if current index isn't a day in this month, make it blank
			if (i < first_day || day > day_count) {
				var curr_date = $("<td class='table-date nil'></td>");
				row.append(curr_date);
			} else {
				var curr_date = $("<td class='table-date'></td>");
				curr_date.text(day);
				var events = check_events(day, month + 1, year);
				if (today === day && $('.active-date').length === 0) {
					curr_date.addClass('active-date');
					show_events(events, months[month], day, year);
				}
				// If this date has any events, style it with .event-date
				if (events.length !== 0) {
					curr_date.addClass('event-date');
				}
				// Set onClick handler for clicking a date
				curr_date.click({ events: events, month: months[month], day: day, year: year }, date_click);
				row.append(curr_date);
			}
		}
		// Append the last row and set the current year
		calendar_days.append(row);
		$('.year').text(year);
	}

	// Get the number of days in a given month/year
	function days_in_month(month, year) {
		var monthStart = new Date(year, month, 1);
		var monthEnd = new Date(year, month + 1, 1);
		return (monthEnd - monthStart) / (1000 * 60 * 60 * 24);
	}

	// Event handler for when logout button is clicked
	function logout_click(event) {
		document.cookie = 'user=;path=/;expires=Thu, 01 Jan 1970 00:00:01 GMT';
		document.cookie = 'user_hash=;path=/;expires=Thu, 01 Jan 1970 00:00:01 GMT';
		window.location.href = window.location.href;
	}

	// Event handler for deleting event
	function delete_event_click(event) {
		$.ajax('/api/event?id=' + encodeURIComponent(event.data.id), {
			method: 'DELETE',
			success: (resp) => {
				if (resp.success) {
					event_data['events'] = event_data['events'].filter((e) => e.id !== event.data.id);
					let date = new Date();
					date.setDate(event.data.day);
					date.setMonth(event.data.month - 1);
					date.setFullYear(event.data.year);
					init_calendar(date);
				} else {
					alert('Error: ' + resp.error);
				}
			},
			error: (_, status, httperr) => {
				if (status === 'error') alert('Request error: ' + httperr);
				else if (status) alert('Request error: ' + status);
				else alert('Request error: unknown reason');
			}
		});
	}

	// Event handler for rejecting an invite
	function reject_invite_click(event) {
		$.ajax('/api/invite?id=' + encodeURIComponent(event.data.id), {
			method: 'DELETE',
			success: (resp) => {
				if (resp.success) {
					const [year, month, day] = event.data.date.split('-').map((e) => parseInt(e));
					let date = new Date();
					date.setDate(day);
					date.setMonth(month - 1);
					date.setFullYear(year);
					init_calendar(date);
				} else {
					alert('Error: ' + resp.error);
				}
			},
			error: (_, status, httperr) => {
				if (status === 'error') alert('Request error: ' + httperr);
				else if (status) alert('Request error: ' + status);
				else alert('Request error: unknown reason');
			}
		});
	}

	// Event handler for accepting an invite
	function accept_invite_click(event) {
		const [year, month, day] = event.data.date.split('-').map((e) => parseInt(e));
		var event_obj = {
			title: event.data.title,
			description: event.data.description,
			year: year,
			month: month,
			day: day
		};

		$.ajax('/api/event', {
			method: 'POST',
			data: event_obj,
			dataType: 'json',
			success: (resp) => {
				if (resp.success) {
					event_data['events'].push({
						id: resp.id,
						...event_obj
					});
					reject_invite_click(event);
				} else {
					alert('Error: ' + resp.error);
				}
			},
			error: (_, status, httperr) => {
				if (status === 'error') alert('Request error: ' + httperr);
				else if (status) alert('Request error: ' + status);
				else alert('Request error: unknown reason');
			}
		});
	}

	// Event handler for when a date is clicked
	function date_click(event) {
		$('.events-container').show(250);
		$('#dialog').hide(250);
		$('.active-date').removeClass('active-date');
		$(this).addClass('active-date');
		show_events(event.data.events, event.data.month, event.data.day, event.data.year);
	}

	// Event handler for when a month is clicked
	function handler_month_click(event) {
		$('.events-container').show(250);
		$('#dialog').hide(250);
		var date = event.data.date;
		$('.active-month').removeClass('active-month');
		$(this).addClass('active-month');
		var new_month = $('.month').index(this);
		date.setMonth(new_month);
		init_calendar(date);
	}

	// Event handler for when the year right-button is clicked
	function handler_next_year(event) {
		$('#dialog').hide(250);
		var date = event.data.date;
		var new_year = date.getFullYear() + 1;
		$('year').html(new_year);
		date.setFullYear(new_year);
		init_calendar(date);
	}

	// Event handler for when the year left-button is clicked
	function handler_prev_year(event) {
		$('#dialog').hide(250);
		var date = event.data.date;
		var new_year = date.getFullYear() - 1;
		$('year').html(new_year);
		date.setFullYear(new_year);
		init_calendar(date);
	}

	// Setup dialog for new invite/event
	function dialog_setup() {
		// remove error highlights on click
		$('input')
			.off()
			.click(function () {
				$(this).removeClass('error-input');
			});

		// setup elements
		$('#dialog-error').hide();
		$("#dialog input[type='text']").val('');
		$('.events-container').hide(250);
		$('#dialog').show(250);

		// Event handler for cancel button
		$('#cancel-button')
			.off()
			.click(function () {
				$('#event-title').removeClass('error-input');
				$('#event-description').removeClass('error-input');
				$('#event-to').removeClass('error-input');
				$('#dialog').hide(250);
				$('.events-container').show(250);
			});
	}

	// Event handler for clicking the new event button
	function handler_new_event(event) {
		// if a date isn't selected do nothing
		if ($('.active-date').length === 0) return;

		dialog_setup();
		$('#dialog-title').text('Create New Event');
		$('#form-invite-only').hide();

		// Event handler for ok button
		$('#ok-button')
			.off()
			.click({ date: event.data.date }, function () {
				var date = event.data.date;
				var title = $('#event-title').val().trim();
				var descr = $('#event-description').val().trim();
				var day = parseInt($('.active-date').html());

				// Basic form validation
				if (title.length === 0) {
					$('#event-title').addClass('error-input');
				} else if (descr.length === 0) {
					$('#event-description').addClass('error-input');
				} else {
					$('#dialog-error').hide();
					create_new_event(title, descr, date, day);
				}
			});
	}

	// Event handler for clicking the new invite button
	function handler_new_invite(event) {
		// if a date isn't selected do nothing
		if ($('.active-date').length === 0) return;

		dialog_setup();
		$('#dialog-title').text('Create New Invite');
		$('#form-invite-only').show();

		// Event handler for ok button
		$('#ok-button')
			.off()
			.click({ date: event.data.date }, function () {
				var date = event.data.date;
				var title = $('#event-title').val().trim();
				var descr = $('#event-description').val().trim();
				var to = $('#event-to').val().trim();
				var day = parseInt($('.active-date').html());

				// Basic form validation
				if (title.length === 0) {
					$('#event-title').addClass('error-input');
				} else if (descr.length === 0) {
					$('#event-description').addClass('error-input');
				} else if (to.length === 0) {
					$('#event-to').addClass('error-input');
				} else {
					$('#dialog-error').hide();
					create_new_invite(to, title, descr, date, day);
				}
			});
	}

	// Push event to server and add to event_data
	function create_new_event(title, description, date, day) {
		var event = {
			title: title,
			description: description,
			date: `${date.getFullYear()}-${date.getMonth() + 1}-${day}`
		};

		$.ajax('/api/event', {
			method: 'POST',
			data: event,
			dataType: 'json',
			success: (resp) => {
				if (resp.success) {
					event_data['events'].push({
						id: resp.id,
						...event
					});
					date.setDate(day);
					init_calendar(date);
					$('#dialog').hide(250);
				} else {
					$('#dialog-error')
						.show()
						.text('Error: ' + resp.error);
				}
			},
			error: (_, status, httperr) => {
				if (status === 'error')
					$('#dialog-error')
						.show()
						.text('Request error: ' + httperr);
				else if (status)
					$('#dialog-error')
						.show()
						.text('Request error: ' + status);
				else $('#dialog-error').show().text('Request error: unknown reason');
			}
		});
	}

	// Push invite to server
	function create_new_invite(to, title, description, date, day) {
		var year = date.getFullYear(),
			month = date.getMonth() + 1;
		var invite = {
			title: title,
			to: to,
			description: description,
			year: year,
			month: month,
			day: day
		};

		$.ajax('/api/invite', {
			method: 'POST',
			data: invite,
			dataType: 'json',
			success: (resp) => {
				if (resp.success) {
					date.setDate(day);
					init_calendar(date);
					$('#dialog').hide(250);
				} else {
					$('#dialog-error')
						.show()
						.text('Error: ' + resp.error);
				}
			},
			error: (_, status, httperr) => {
				if (status === 'error')
					$('#dialog-error')
						.show()
						.text('Request error: ' + httperr);
				else if (status)
					$('#dialog-error')
						.show()
						.text('Request error: ' + status);
				else $('#dialog-error').show().text('Request error: unknown reason');
			}
		});
	}

	// Display all events of the selected date in card views
	function show_events(events, month, day, year) {
		$('.events-container').empty();
		$('.events-container').show(250);
		$.ajax(`/api/invites?date=${year}-${months.indexOf(month) + 1}-${day}`, {
			success: (resp) => {
				// Clear the dates container
				$('.events-container').empty();
				$('.events-container').show(250);
				// If there are no events for this date, notify the user
				if (events.length === 0) {
					var event_card = $("<div class='event-card'></div>");
					var event_title = $("<div class='event-title'></div>");
					event_title.text('No events planned for ' + month + ' ' + day + '.');
					$(event_card).css({ 'border-left': '10px solid #FF1744' });
					$(event_card).append(event_title);
					$('.events-container').append(event_card);
				} else {
					// Go through and add each event as a card to the events container
					for (var i = 0; i < events.length; i++) {
						var event_card = $("<div class='event-card'></div>");
						var event_title = $("<div class='event-title'></div>");
						var event_descr = $("<div class='event-descr'></div>");
						var event_delete = $("<button class='event-delete btn btn-sm btn-danger'>X</button>");
						event_delete.click(
							{ id: events[i].id, year: events[i].year, month: events[i].month, day: events[i].day },
							delete_event_click
						);
						event_title.text(events[i]['title'] + ':');
						event_descr.text(events[i]['description']);
						event_card.append(event_title).append(event_descr).append(event_delete);
						$('.events-container').append(event_card);
					}
				}

				if (resp.success) {
					const invites = resp.invites;
					for (var i = 0; i < invites.length; i++) {
						var event_card = $("<div class='invite-card'></div>");
						var event_inviter = $("<div class='invite-from'></div>");
						var event_title = $("<div class='invite-title'></div>");
						var event_descr = $("<div class='invite-descr'></div>");
						var button_container = $("<div class='invite-buttons'></div>");
						var accept = $("<button class='invite-accept btn btn-sm btn-success'>Accept</button>");
						var reject = $("<button class='invite-reject btn btn-sm btn-danger'>Reject</button>");

						reject.click({ id: invites[i].id, date: invites[i].date }, reject_invite_click);
						accept.click(
							{
								id: invites[i].id,
								date: invites[i].date,
								title: invites[i].title,
								description: invites[i].description
							},
							accept_invite_click
						);

						event_inviter.text(invites[i]['from'] + ' invited you to an event:');
						event_title.text(invites[i]['title'] + ':');
						event_descr.text(invites[i]['description']);

						button_container.append(accept).append(reject);
						event_card
							.append(event_inviter)
							.append(event_title)
							.append(event_descr)
							.append(button_container);
						$('.events-container').append(event_card);
					}
				} else {
					alert('Error: ' + resp.error);
				}
			},
			error: (_, status, httperr) => {
				if (status === 'error') alert('Request error: ' + httperr);
				else if (status) alert('Request error: ' + status);
				else alert('Request error: unknown reason');
			}
		});
	}

	// Checks if a specific date has any events
	function check_events(day, month, year) {
		var events = [];
		for (var i = 0; i < event_data['events'].length; i++) {
			var event = event_data['events'][i];
			if (event['day'] === day && event['month'] === month && event['year'] === year) {
				events.push(event);
			}
		}
		return events;
	}

	const months = [
		'January',
		'February',
		'March',
		'April',
		'May',
		'June',
		'July',
		'August',
		'September',
		'October',
		'November',
		'December'
	];
})(jQuery);
