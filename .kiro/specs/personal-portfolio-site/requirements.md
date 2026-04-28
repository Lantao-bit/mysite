# Requirements Document

## Introduction

A personal portfolio website built with Python (Flask), Bootstrap, and SQLite. The site serves as a professional launch page that showcases the owner's professional information and application portfolio. Visitors can browse the portfolio and read comments. Authenticated visitors can leave comments.

## Glossary

- **Portfolio_Site**: The personal portfolio web application built with Python (Flask), Bootstrap, and SQLite
- **Professional_Section**: The area of the page displaying the owner's professional information (name, bio, skills, contact details)
- **Portfolio_Section**: The area of the page displaying the owner's application portfolio with project entries
- **Project_Entry**: A single portfolio item representing an application or project, including title, description, image, and link
- **Comment_Section**: The area of the page where visitor comments are displayed and submitted
- **Comment**: A visitor-submitted message associated with the portfolio site, stored in the SQLite database
- **Visitor**: Any person browsing the Portfolio_Site
- **Authenticated_Visitor**: A Visitor who has logged in with valid credentials
- **Authentication_System**: The component responsible for user registration, login, logout, and session management
- **SQLite_Database**: The local SQLite database storing Project_Entry records, Comment records, and user accounts

## Requirements

### Requirement 1: Display Professional Information

**User Story:** As a visitor, I want to see the site owner's professional information, so that I can learn about their background and skills.

#### Acceptance Criteria

1. THE Portfolio_Site SHALL display the owner's name, job title, photo and a professional bio in the Professional_Section
2. THE Portfolio_Site SHALL display a list of skills in the Professional_Section
3. THE Portfolio_Site SHALL display contact information (email, links to social profiles) in the Professional_Section
4. THE Portfolio_Site SHALL render the Professional_Section using Bootstrap responsive layout components so that the content is readable on desktop and mobile devices

### Requirement 2: Display Application Portfolio

**User Story:** As a visitor, I want to browse the owner's application portfolio, so that I can see examples of their work.

#### Acceptance Criteria

1. THE Portfolio_Site SHALL display all Project_Entry records from the SQLite_Database in the Portfolio_Section
2. THE Portfolio_Site SHALL display each Project_Entry with its title, description, and an optional image
3. WHEN a Project_Entry includes an external link, THE Portfolio_Site SHALL render the link as a clickable element that opens in a new browser tab
4. THE Portfolio_Site SHALL render the Portfolio_Section using a Bootstrap card-based grid layout that adapts to the screen width

### Requirement 3: User Registration

**User Story:** As a visitor, I want to create an account, so that I can log in and leave comments.

#### Acceptance Criteria

1. THE Authentication_System SHALL provide a registration form requesting a username, email, and password
2. WHEN a Visitor submits a valid registration form, THE Authentication_System SHALL create a new user record in the SQLite_Database
3. WHEN a Visitor submits a registration form with a username or email that already exists, THE Authentication_System SHALL display an error message indicating the conflict
4. THE Authentication_System SHALL store passwords as salted hashes in the SQLite_Database
5. WHEN a Visitor submits a registration form with a password shorter than 8 characters, THE Authentication_System SHALL display a validation error message

### Requirement 4: User Login and Logout

**User Story:** As a registered visitor, I want to log in and out, so that I can manage my authenticated session.

#### Acceptance Criteria

1. THE Authentication_System SHALL provide a login form requesting a username and password
2. WHEN a Visitor submits valid login credentials, THE Authentication_System SHALL create an authenticated session and redirect the Visitor to the main page
3. WHEN a Visitor submits invalid login credentials, THE Authentication_System SHALL display an error message indicating that the credentials are incorrect
4. WHEN an Authenticated_Visitor clicks the logout control, THE Authentication_System SHALL terminate the session and redirect the Visitor to the main page
5. THE Portfolio_Site SHALL display the logged-in username and a logout control in the navigation bar WHILE a session is active

### Requirement 5: Display Comments

**User Story:** As a visitor, I want to read comments left by others, so that I can see community feedback on the portfolio.

#### Acceptance Criteria

1. THE Portfolio_Site SHALL display all Comment records from the SQLite_Database in the Comment_Section, ordered from newest to oldest
2. THE Portfolio_Site SHALL display each Comment with the author's username and the submission date
3. WHEN a new Comment is submitted, THE Comment_Section SHALL include the new Comment without requiring a full page reload or after a page redirect

### Requirement 6: Submit Comments

**User Story:** As an authenticated visitor, I want to leave a comment, so that I can share feedback on the portfolio.

#### Acceptance Criteria

1. WHILE a Visitor is authenticated, THE Portfolio_Site SHALL display a comment submission form in the Comment_Section
2. WHILE a Visitor is not authenticated, THE Portfolio_Site SHALL display a prompt to log in instead of the comment submission form
3. WHEN an Authenticated_Visitor submits a non-empty comment, THE Portfolio_Site SHALL store the Comment in the SQLite_Database with the author's username and the current timestamp
4. WHEN an Authenticated_Visitor submits an empty comment, THE Portfolio_Site SHALL display a validation error and not store the Comment
5. IF the SQLite_Database is unavailable when a Comment is submitted, THEN THE Portfolio_Site SHALL display an error message indicating that the comment could not be saved

### Requirement 7: Navigation and Layout

**User Story:** As a visitor, I want a clear and consistent page layout, so that I can easily find the professional information, portfolio, and comments sections.

#### Acceptance Criteria

1. THE Portfolio_Site SHALL include a Bootstrap navigation bar with links to the Professional_Section, Portfolio_Section, and Comment_Section
2. THE Portfolio_Site SHALL use a single-page layout with anchor-based scrolling to each section
3. THE Portfolio_Site SHALL include a footer with copyright information

### Requirement 8: Data Persistence

**User Story:** As the site owner, I want all data stored reliably, so that portfolio entries and comments persist across server restarts.

#### Acceptance Criteria

1. THE Portfolio_Site SHALL initialize the SQLite_Database schema on first run, creating tables for users, Project_Entry records, and Comment records
2. THE Portfolio_Site SHALL use parameterized queries for all SQLite_Database operations to prevent SQL injection
3. IF the SQLite_Database file does not exist at startup, THEN THE Portfolio_Site SHALL create the database file and initialize the schema
