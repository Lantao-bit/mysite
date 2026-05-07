# Requirements Document

## Introduction

This feature adds admin-level CRUD operations for portfolio entries (projects) in the Flask portfolio site. The site owner needs the ability to create, edit, and delete portfolio entries through a web interface, as well as export entries as JSON for backup and import them back from JSON files. All management operations are restricted to the admin user, identified by a configured email address in the Flask app config.

## Glossary

- **Portfolio_Manager**: The set of route handlers and UI components responsible for managing portfolio entries (projects)
- **Project**: A portfolio entry stored in the `projects` table with fields: title, description, image_url, external_link, display_order
- **Authenticated_User**: A user who has successfully logged in via Flask-Login and holds a valid session
- **Admin_User**: An Authenticated_User whose email address matches the ADMIN_EMAIL value in the Flask app configuration
- **ADMIN_EMAIL**: A Flask application configuration value (`app.config['ADMIN_EMAIL']`) containing the site owner's email address, used to determine admin access
- **Export_Service**: The component responsible for serializing project records into a downloadable JSON file
- **Import_Service**: The component responsible for parsing an uploaded JSON file and creating project records from it
- **Project_Form**: The Flask-WTF form used for creating and editing project entries with CSRF protection

## Requirements

### Requirement 1: Create Portfolio Entry

**User Story:** As the site owner, I want to create new portfolio entries through a web form, so that I can showcase new projects on my portfolio page.

#### Acceptance Criteria

1. WHEN an Admin_User submits the Project_Form with valid data, THE Portfolio_Manager SHALL create a new Project record in the database and redirect to the portfolio management page with a success message.
2. WHEN an Admin_User submits the Project_Form with missing required fields (title or description), THE Portfolio_Manager SHALL re-render the form displaying field-specific validation errors.
3. THE Project_Form SHALL include fields for title, description, image_url, external_link, and display_order.
4. THE Portfolio_Manager SHALL protect the create route with admin authorization so that unauthenticated requests are redirected to the login page and non-admin authenticated requests receive a 403 response.

### Requirement 2: Edit Portfolio Entry

**User Story:** As the site owner, I want to edit existing portfolio entries, so that I can keep my project information up to date.

#### Acceptance Criteria

1. WHEN an Admin_User submits the Project_Form with valid updated data for an existing Project, THE Portfolio_Manager SHALL update the corresponding Project record in the database and redirect to the portfolio management page with a success message.
2. WHEN an Admin_User requests the edit page for an existing Project, THE Portfolio_Manager SHALL pre-populate the Project_Form with the current field values of that Project.
3. IF an Admin_User requests the edit page for a non-existent Project, THEN THE Portfolio_Manager SHALL return a 404 response.
4. THE Portfolio_Manager SHALL protect the edit route with admin authorization so that unauthenticated requests are redirected to the login page and non-admin authenticated requests receive a 403 response.

### Requirement 3: Delete Portfolio Entry

**User Story:** As the site owner, I want to delete portfolio entries, so that I can remove outdated or irrelevant projects from my portfolio.

#### Acceptance Criteria

1. WHEN an Admin_User submits a delete request for an existing Project, THE Portfolio_Manager SHALL remove the Project record from the database and redirect to the portfolio management page with a success message.
2. IF an Admin_User submits a delete request for a non-existent Project, THEN THE Portfolio_Manager SHALL return a 404 response.
3. THE Portfolio_Manager SHALL protect the delete route with admin authorization so that unauthenticated requests are redirected to the login page and non-admin authenticated requests receive a 403 response.
4. THE Portfolio_Manager SHALL require the delete request to use the HTTP POST method to prevent accidental deletion via GET requests.

### Requirement 4: List Portfolio Entries for Management

**User Story:** As the site owner, I want to view all portfolio entries in a management interface, so that I can see what projects exist and access edit/delete/export actions.

#### Acceptance Criteria

1. WHEN an Admin_User navigates to the portfolio management page, THE Portfolio_Manager SHALL display all Project records in a table ordered by display_order.
2. THE Portfolio_Manager SHALL display the title, description (truncated), display_order, and action links (edit, delete) for each Project in the management table.
3. THE Portfolio_Manager SHALL protect the management list route with admin authorization so that unauthenticated requests are redirected to the login page and non-admin authenticated requests receive a 403 response.

### Requirement 5: Export Portfolio Entries as JSON

**User Story:** As the site owner, I want to download all portfolio entries as a JSON file, so that I can back up my project data or transfer it to another environment.

#### Acceptance Criteria

1. WHEN an Admin_User requests the export endpoint, THE Export_Service SHALL serialize all Project records into a JSON array and return it as a downloadable file with Content-Disposition header set to attachment.
2. THE Export_Service SHALL include all Project fields (title, description, image_url, external_link, display_order) in each exported record.
3. THE Export_Service SHALL exclude internal database fields (id) from the exported JSON to allow clean re-import.
4. THE Portfolio_Manager SHALL protect the export route with admin authorization so that unauthenticated requests are redirected to the login page and non-admin authenticated requests receive a 403 response.

### Requirement 6: Import Portfolio Entries from JSON

**User Story:** As the site owner, I want to upload a JSON file containing portfolio entries, so that I can restore backed-up projects or bulk-add new entries.

#### Acceptance Criteria

1. WHEN an Admin_User uploads a valid JSON file containing an array of project objects, THE Import_Service SHALL create a new Project record for each object in the array and redirect to the portfolio management page with a success message indicating the count of imported entries.
2. IF an Admin_User uploads a file that is not valid JSON, THEN THE Import_Service SHALL display an error message indicating the file format is invalid.
3. IF an Admin_User uploads a JSON file where any entry is missing required fields (title or description), THEN THE Import_Service SHALL display an error message identifying the invalid entries and not import any records.
4. THE Import_Service SHALL accept project objects with fields: title, description, image_url (optional), external_link (optional), display_order (optional, defaults to 0).
5. THE Portfolio_Manager SHALL protect the import route with admin authorization so that unauthenticated requests are redirected to the login page and non-admin authenticated requests receive a 403 response.

### Requirement 7: JSON Round-Trip Integrity

**User Story:** As the site owner, I want exported JSON to be re-importable without data loss, so that backup and restore operations are reliable.

#### Acceptance Criteria

1. FOR ALL valid sets of Project records, exporting via the Export_Service then importing via the Import_Service SHALL produce Project records with equivalent field values to the originals (round-trip property).
2. THE Export_Service SHALL produce JSON output that conforms to the schema expected by the Import_Service.

### Requirement 8: Admin Authorization

**User Story:** As the site owner, I want portfolio management features restricted to my account only, so that visitors cannot modify my portfolio even if they register and log in.

#### Acceptance Criteria

1. THE Flask application configuration SHALL contain an ADMIN_EMAIL setting that holds the site owner's email address.
2. WHEN an Authenticated_User whose email matches the ADMIN_EMAIL accesses a portfolio management route, THE Portfolio_Manager SHALL grant access and process the request.
3. WHEN an Authenticated_User whose email does not match the ADMIN_EMAIL attempts to access a portfolio management route, THE Portfolio_Manager SHALL deny access with a 403 Forbidden response.
4. WHEN an unauthenticated user attempts to access a portfolio management route, THE Portfolio_Manager SHALL redirect the request to the login page.
5. WHILE the current user is the Admin_User, THE Portfolio_Manager SHALL display portfolio management navigation links in the navigation bar.
6. WHILE the current user is not the Admin_User, THE Portfolio_Manager SHALL hide portfolio management navigation links from the navigation bar.
