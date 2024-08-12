# ReviewMate-REST-API

ReviewMate REST API
Overview
This project involves designing, implementing, and deploying a RESTful API for a business review site. The API supports full CRUD operations for managing businesses and reviews, with MySQL used for data storage. The API is deployed using a Docker container on a virtual machine created with Google Compute Engine (GCE), a part of Google Cloud Platform (GCP).

Key Features
Resource Representation with Links: All resource representations include complete URLs, making the API more user-friendly and navigable.
Pagination: The API supports paginated results for listing businesses, returning 3 businesses per page, with navigation links to subsequent pages.
CRUD Operations: The API provides comprehensive CRUD functionality for both business and review resources.
Endpoints
Create a Business:
The response includes a self URL pointing to the created business.
Get a Business:
The response includes a self URL pointing to the requested business.
List All Businesses:
The response is paginated, returning 3 businesses per page, each with a self URL.
The response includes a next property to navigate to the next page.
Edit a Business:
The response includes a self URL pointing to the edited business.
Delete a Business:
Removes the specified business from the database.
List All Businesses for an Owner:
Not paginated. Each business includes a self URL.
Create a Review:
The response includes self and business URLs, linking to the review and the business being reviewed.
Get a Review:
The response includes a self URL pointing to the requested review.
Edit a Review:
The response includes a self URL pointing to the edited review.
Delete a Review:
Removes the specified review from the database.
List All Reviews for a User:
Not paginated. Each review includes self and business URLs.
Data Model
MySQL is used to store data for businesses and reviews.
Foreign key constraints ensure reviews can only be created for existing businesses.
Uniqueness constraints ensure a user can submit only one review per business.
URLs for resources are generated programmatically and are not stored in the database.
Deployment
Docker is used for containerization, allowing for consistent deployment across environments.
The application is deployed on a Google Compute Engine (GCE) virtual machine, utilizing GCP infrastructure.
Environment variables are configured in the Dockerfile to manage database connections and secure Google Cloud credentials.
Testing
The API is thoroughly tested using Postman collections and automated tests with Newman, ensuring robust error handling and correct implementation of all endpoints.
The API supports testing both locally and on the deployed GCP instance, with configurable URLs for easy environment switching.
