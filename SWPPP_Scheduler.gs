/**
 * SWPPP Inspection Reminder Scheduler
 * =====================================
 * Sends an inspection reminder email to lbbartee@gmail.com every
 * Monday and Thursday at 8 AM Eastern through August 2027.
 *
 * HOW TO SET UP (one-time):
 * 1. Replace all code in this project with this file
 * 2. Save (Ctrl+S)
 * 3. Select "setupTriggers" in the dropdown and click Run
 * 4. Authorize when prompted — done!
 *
 * To test immediately: Select "sendInspectionReminder" and click Run.
 * To stop: Go to Triggers (clock icon) and delete both triggers.
 */

// ─── CONFIGURATION ────────────────────────────────────────────────────────────
var CONFIG = {
  inspectorEmail:  "lbbartee@gmail.com",
  ccEmail:         "yara.llbdesign@gmail.com",
  projectLocation: "9561 Springs Road, Warrenton, VA 20186",
  inspectorName:   "Lucas Bartee",
  formUrl:         "https://7861-i0wo5nb4yh6gb17w4aizq-744f7aaf.us1.manus.computer",
  // Schedule ends after August 2027 (~18 months from March 2026)
  endDate:         new Date("2027-09-01T00:00:00")
};

// ─── MAIN SEND FUNCTION ───────────────────────────────────────────────────────
/**
 * Sends the inspection reminder email.
 * Called by both the Monday and Thursday triggers.
 */
function sendInspectionReminder() {
  // Stop sending after end date
  var today = new Date();
  if (today >= CONFIG.endDate) {
    Logger.log("Schedule complete — past end date of August 2027. No email sent.");
    return;
  }

  var dateStr = Utilities.formatDate(today, "America/New_York", "EEEE, MMMM d, yyyy");

  // Calculate next inspection day (next Mon or Thu)
  var dayOfWeek = parseInt(Utilities.formatDate(today, "America/New_York", "u")); // 1=Mon, 7=Sun
  var daysUntilNext;
  if (dayOfWeek === 1) {
    // Today is Monday — next is Thursday (3 days)
    daysUntilNext = 3;
  } else if (dayOfWeek === 4) {
    // Today is Thursday — next is Monday (4 days)
    daysUntilNext = 4;
  } else {
    // Fallback: next Monday
    daysUntilNext = (8 - dayOfWeek) % 7 || 7;
  }
  var nextDate = new Date(today.getTime() + daysUntilNext * 24 * 60 * 60 * 1000);
  var nextDateStr = Utilities.formatDate(nextDate, "America/New_York", "EEEE, MMMM d, yyyy");

  var subject = "SWPPP Inspection Due \u2014 " + dateStr + " | 9561 Springs Road";

  var htmlBody = [
    '<!DOCTYPE html><html><head>',
    '<style>',
    'body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px;}',
    '.container{background:white;border-radius:8px;padding:30px;max-width:600px;margin:0 auto;box-shadow:0 2px 8px rgba(0,0,0,0.1);}',
    '.header{background:#1a5276;color:white;padding:20px;border-radius:6px 6px 0 0;margin:-30px -30px 20px -30px;}',
    '.header h1{margin:0;font-size:22px;}',
    '.header p{margin:5px 0 0;opacity:0.85;font-size:14px;}',
    '.info-box{background:#eaf4fb;border-left:4px solid #1a5276;padding:15px;margin:20px 0;border-radius:0 4px 4px 0;}',
    '.info-box p{margin:5px 0;font-size:14px;}',
    '.btn{display:inline-block;background:#1a5276;color:white;padding:14px 28px;border-radius:6px;text-decoration:none;font-size:16px;font-weight:bold;margin:20px 0;}',
    '.footer{font-size:12px;color:#888;margin-top:20px;border-top:1px solid #eee;padding-top:15px;}',
    '</style></head><body>',
    '<div class="container">',
    '<div class="header"><h1>SWPPP Inspection Due</h1><p>' + dateStr + '</p></div>',
    '<p>Your SWPPP stormwater inspection report is due today. Please complete the site inspection and submit the report.</p>',
    '<div class="info-box">',
    '<p><strong>Project:</strong> ' + CONFIG.projectLocation + '</p>',
    '<p><strong>Inspector:</strong> ' + CONFIG.inspectorName + '</p>',
    '<p><strong>Schedule:</strong> Every Monday &amp; Thursday</p>',
    '</div>',
    '<p>Click the button below to open the inspection form. Today\'s weather data will be automatically populated.</p>',
    '<a href="' + CONFIG.formUrl + '" class="btn">Open Inspection Form &rarr;</a>',
    '<div class="footer">',
    '<p>Next inspection due: <strong>' + nextDateStr + '</strong></p>',
    '<p>This is an automated reminder from your SWPPP Inspection Workflow &mdash; Fauquier County.</p>',
    '</div></div></body></html>'
  ].join('');

  var options = {
    htmlBody: htmlBody,
    cc: CONFIG.ccEmail,
    name: "SWPPP Inspection Workflow"
  };

  GmailApp.sendEmail(CONFIG.inspectorEmail, subject, "", options);
  Logger.log("Reminder sent to " + CONFIG.inspectorEmail + " (CC: " + CONFIG.ccEmail + ") on " + dateStr);
}

// ─── TRIGGER SETUP ────────────────────────────────────────────────────────────
/**
 * Run this ONCE to install two triggers: one for Monday, one for Thursday.
 * Both fire at 8 AM Eastern.
 */
function setupTriggers() {
  // Delete all existing triggers for this project
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }

  // Monday at 8 AM Eastern
  ScriptApp.newTrigger("sendInspectionReminder")
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(8)
    .inTimezone("America/New_York")
    .create();

  // Thursday at 8 AM Eastern
  ScriptApp.newTrigger("sendInspectionReminder")
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.THURSDAY)
    .atHour(8)
    .inTimezone("America/New_York")
    .create();

  Logger.log("Two triggers installed:");
  Logger.log("  - Every Monday at 8 AM Eastern");
  Logger.log("  - Every Thursday at 8 AM Eastern");
  Logger.log("Schedule runs through August 2027.");
}
