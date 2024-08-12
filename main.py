# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from dotenv import load_dotenv
import logging
import os

from flask import Flask, request, url_for

import sqlalchemy

from connect_connector import connect_with_connector

#load variables from .env into environment
load_dotenv()

BUSINESSES = 'businesses'
REVIEWS = 'reviews'
ERROR_NOT_FOUND = {'Error' : 'No business with this business_id exists'}
ERROR_REVIEW_NOT_FOUND = {"Error": "No review with this review_id exists"}
ERROR_BAD_REQUEST = {'Error': 'The request body is missing at least one of the required attributes'}
ERROR_CONFLICT = {"Error": "You have already submitted a review for this business. You can update your previous review, or delete it and submit a new review"}

app = Flask(__name__)

logger = logging.getLogger()

# Sets up connection pool for the app
def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    if os.environ.get('INSTANCE_CONNECTION_NAME'):
        return connect_with_connector()
        
    raise ValueError(
        'Missing database connection type. Please define INSTANCE_CONNECTION_NAME'
    )

# This global variable is declared with a value of `None`
db = None

# Initiates connection to database
def init_db():
    global db
    db = init_connection_pool()

# create 'lodgings' table in database if it does not already exist
def create_table(db: sqlalchemy.engine.base.Engine) -> None:
    with db.connect() as conn:
        conn.execute(
            sqlalchemy.text("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id SERIAL PRIMARY KEY,
                    owner_id INT NOT NULL,
                    name VARCHAR(50) NOT NULL,
                    street_address VARCHAR(100) NOT NULL,
                    city VARCHAR(50) NOT NULL,
                    state VARCHAR(2) NOT NULL,
                    zip_code VARCHAR(5) NOT NULL
                );
            """)
        )

        conn.execute(
            sqlalchemy.text("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    user_id INT NOT NULL,
                    business_id INT NOT NULL REFERENCES businesses(id),
                    stars INT CHECK (stars BETWEEN 0 and 5),
                    review_text VARCHAR(1000) DEFAULT NULL
                );
            """)
        )


        conn.commit()




@app.route('/')
def index():
    return 'Please navigate to /businesses to use this API'




# Create a business
@app.route('/' + BUSINESSES, methods=['POST'])
def post_businesses():
    content = request.get_json()

    try:
        # Using a with statement ensures that the connection is always released
        # back into the pool at the end of statement (even if an error occurs)
        with db.connect() as conn:
            # Preparing a statement before hand can help protect against injections.
            stmt = sqlalchemy.text(
                'INSERT INTO businesses(owner_id, name, street_address, city, state, zip_code) '
                ' VALUES (:owner_id, :name, :street_address, :city, :state, :zip_code)'
            )
            # connection.execute() automatically starts a transaction
            conn.execute(stmt, parameters={'owner_id': content['owner_id'],
                                        'name': content['name'], 
                                        'street_address': content['street_address'], 
                                        'city': content['city'],
                                        'state': content['state'],
                                        'zip_code': content['zip_code']})
            # The function last_insert_id() returns the most recent value
            # generated for an `AUTO_INCREMENT` column when the INSERT 
            # statement is executed
            stmt2 = sqlalchemy.text('SELECT last_insert_id()')
            # scalar() returns the first column of the first row or None if there are no rows
            business_id = conn.execute(stmt2).scalar()
            # Remember to commit the transaction
            conn.commit()
        
        #construct url
        base_url = request.base_url
        complete_url = f"{base_url}/{business_id}"

        return ({'id': business_id,
                'owner_id': content['owner_id'],
                'name': content['name'], 
                'street_address': content['street_address'], 
                'city': content['city'],
                'state': content['state'],
                'zip_code': content['zip_code'],
                'self': complete_url}, 201)
    
    except KeyError as e:
        return (ERROR_BAD_REQUEST, 400)
    
    except Exception as e:
        logger.exception(e)
        return ({'Error': 'Unable to create business'}, 500)


# get a business
@app.route('/' + BUSINESSES + '/<int:id>', methods=['GET'])
def get_business(id):
    with db.connect() as conn:
        stmt = sqlalchemy.text(
                'SELECT * FROM businesses WHERE id=:id'
            )
        # one_or_none returns at most one result or raise an exception.
        # returns None if the result has no rows.
        row = conn.execute(stmt, parameters={'id': id}).one_or_none()
        if row is None:
            return ERROR_NOT_FOUND, 404
        else:
            business = row._asdict()

            business['zip_code'] = int(business['zip_code'])

            root_url = request.url_root
            complete_url = f"{root_url}businesses/{id}"
            business['self'] = complete_url
        
        
            return business, 200


#update a business
@app.route('/' + BUSINESSES + '/<int:id>', methods=['PUT'])
def put_business(id):

    try:
        with db.connect() as conn:
            stmt = sqlalchemy.text(
                    'SELECT * FROM businesses WHERE id=:id'
                )
            row = conn.execute(stmt, parameters={'id': id}).one_or_none()
            if row is None:
                return ERROR_NOT_FOUND, 404
            else:
                content = request.get_json()
                stmt = sqlalchemy.text(
                    'UPDATE businesses '
                    'SET owner_id = :owner_id, name = :name, street_address = :street_address, city = :city, state = :state, zip_code = :zip_code '
                    'WHERE id = :id'
                )
                conn.execute(stmt, parameters={'owner_id': content['owner_id'],
                                            'name': content['name'], 
                                            'street_address': content['street_address'], 
                                            'city': content['city'],
                                            'state': content['state'],
                                            'zip_code': content['zip_code'],
                                            'id': id})
                                            
                conn.commit()
                root_url = request.url_root
                complete_url = f"{root_url}businesses/{id}"

                return {'id': id,
                'owner_id': content['owner_id'],
                'name': content['name'], 
                'street_address': content['street_address'], 
                'city': content['city'],
                'state': content['state'],
                'zip_code': content['zip_code'],
                'self': complete_url}
            
    except KeyError as e:
        return (ERROR_BAD_REQUEST, 400)
    
    except Exception as e:
        logger.exception(e)
        return {'Error': 'Unable to create business'}, 500





# delete a business
@app.route('/' + BUSINESSES + '/<int:id>', methods=['DELETE'])
def delete_business(id):
    with db.connect() as conn:

        delete_review_stmt = sqlalchemy.text(
                'DELETE FROM reviews WHERE business_id=:id'
            )
        conn.execute(delete_review_stmt, {'id': id})

        stmt = sqlalchemy.text(
                'DELETE FROM businesses WHERE id=:id'
            )

        result = conn.execute(stmt, parameters={'id': id})
        conn.commit()
        
        if result.rowcount == 1:
            return ('', 204)
        else:
            return ERROR_NOT_FOUND, 404
        




# list all businesses
@app.route('/' + BUSINESSES, methods=['GET'])
def get_businesses():
    with db.connect() as conn:
        # pagination - create offset and limit
        offset = request.args.get('offset', default=0, type=int)
        limit = request.args.get('limit', default=3, type=int)

        
        stmt = sqlalchemy.text(
            'SELECT * FROM businesses LIMIT :limit OFFSET :offset'
        )
        rows = conn.execute(stmt, {'limit': limit + 1, 'offset': offset}).fetchall()
        
        businesses = []
        for row in rows[:limit]:  # Only return up to 'limit' businesses
            business = row._asdict()
            business['zip_code'] = int(business['zip_code'])
            
            
            root_url = request.url_root
            business['self'] = f"{root_url}businesses/{business['id']}"
            
            businesses.append(business)

        
        response_data = {'entries': businesses}
        if len(rows) > limit:
            next_offset = offset + limit
            next_url = f"{request.base_url}?offset={next_offset}&limit={limit}"
            response_data['next'] = next_url

        return response_data, 200





# list all businesses for an owner
@app.route('/owners/<int:id>/' + BUSINESSES, methods=['GET'])
def get_bussiness_by_owner(id):
    with db.connect() as conn:
        stmt = sqlalchemy.text(
                'SELECT * FROM businesses WHERE owner_id = :owner_id'
            )
        
        result = conn.execute(stmt, parameters={'owner_id': id})
        conn.commit()

        businesses = []
        

        for row in result.fetchall():
            business = row._asdict()
            
            business['self'] = request.url_root + f"businesses/{business['id']}"
            businesses.append(business)

        return businesses

################REVIEWS


# create a review
@app.route('/' + REVIEWS, methods=['POST'])
def post_review():
    content = request.get_json()


    required_fields = ['user_id', 'business_id', 'stars']
    missing_fields = [field for field in required_fields if field not in content]

    if missing_fields:
        return ERROR_BAD_REQUEST, 400
    

    try:
        
        with db.connect() as conn:

            business_check = sqlalchemy.text(
                'SELECT 1 FROM businesses ' 
                'WHERE id = :business_id '
            )
            if not conn.execute(business_check, {'business_id': content['business_id']}).scalar():
                return ERROR_NOT_FOUND, 404


            # check if review exists
            check_stmt = sqlalchemy.text("""
                SELECT 1 FROM reviews 
                WHERE user_id = :user_id AND business_id = :business_id;
            """)
            existing_review = conn.execute(check_stmt, {
                'user_id': content['user_id'],
                'business_id': content['business_id']
            }).fetchone()
            
            if existing_review:
                return ERROR_CONFLICT, 409



            
            stmt = sqlalchemy.text("""
                INSERT INTO reviews (user_id, business_id, stars, review_text)
                VALUES (:user_id, :business_id, :stars, :review_text);
            """)
            
            
            conn.execute(stmt, parameters={'user_id': content['user_id'],
                                        'business_id': content['business_id'], 
                                        'stars': content['stars'], 
                                        'review_text': content.get('review_text', '')})
            


            stmt2 = sqlalchemy.text('SELECT last_insert_id()')
            # scalar() returns the first column of the first row or None if there are no rows
            review_id = conn.execute(stmt2).scalar()

            conn.commit()
        
        
        #construct url for review
        base_url = request.base_url
        complete_url = f"{base_url}/{review_id}"

        # business url
        business_url = f"{request.host_url}{'businesses/'}{content['business_id']}"

        return ({'id': review_id,
                'user_id': content['user_id'],
                'business': business_url, 
                'stars': content['stars'], 
                'review_text': content.get('review_text', ''),
                'self': complete_url}, 201)
    
    except KeyError as e:
        return ERROR_BAD_REQUEST, 400
    
    except Exception as e:
        logger.exception(e)
        print(f"Error occurred: {e}")
        return {'Error': 'Unable to create review'}, 500


# get a review
@app.route('/' + REVIEWS + '/<int:id>', methods=['GET'])
def get_review(id):
    with db.connect() as conn:
        stmt = sqlalchemy.text(
                'SELECT * FROM reviews WHERE id=:id'
            )
        
        row = conn.execute(stmt, parameters={'id': id}).one_or_none()
        if row is None:
            return ERROR_REVIEW_NOT_FOUND, 404
        
        review = row._asdict()

        # review['zip_code'] = int(review['zip_code'])

        business_url = f"{request.host_url}businesses/{review['business_id']}"
        review_url = f"{request.host_url}reviews/{id}"

        # updated return
        review_response = {
            "id": review['id'],
            "user_id": review['user_id'],
            "business": business_url,
            "stars": review['stars'],
            "review_text": review['review_text'],
            "self": review_url
        }
    
    
        return review_response, 200






# Edit review
@app.route('/' + REVIEWS + '/<int:id>', methods=['PUT'])
def put_review(id):

    content = request.get_json()

    if 'stars' not in content:
        return ERROR_BAD_REQUEST, 400

    
    update_parts = []
    update_params = {}
    if 'stars' in content:
        update_parts.append('stars = :stars')
        update_params['stars'] = content['stars']
    if 'review_text' in content:
        update_parts.append('review_text = :review_text')
        update_params['review_text'] = content['review_text']

    
    if not update_parts:
        return {'Error': 'No valid fields provided to update'}, 400

    update_params['id'] = id
        
    with db.connect() as conn:
        # Check if the review exists
        exists_check = sqlalchemy.text('SELECT 1 FROM reviews WHERE id = :id')
        exists = conn.execute(exists_check, {'id': id}).scalar()
        if not exists:
            return ERROR_REVIEW_NOT_FOUND, 404

        # Perform the update
        update_stmt = sqlalchemy.text('UPDATE reviews SET ' + ', '.join(update_parts) + ' WHERE id = :id')
        conn.execute(update_stmt, update_params)
        conn.commit()

        # Retrieve the updated review to return
        review_stmt = sqlalchemy.text('SELECT * FROM reviews WHERE id = :id')
        row = conn.execute(review_stmt, {'id': id}).one_or_none()

        if row is None:
            return ERROR_REVIEW_NOT_FOUND, 404
        else:
            review = row._asdict()

        business_url = f"{request.host_url}businesses/{review['business_id']}"
        review_url = f"{request.host_url}reviews/{id}"

        
        review_response = {
            "id": review['id'],
            "user_id": review['user_id'],
            "business": business_url,
            "stars": review['stars'],
            "review_text": review.get('review_text', ''),
            "self": review_url
        }
        
        return review_response, 200
            





# delete a review
@app.route('/' + REVIEWS + '/<int:id>', methods=['DELETE'])
def delete_review(id):
    with db.connect() as conn:
        
        stmt = sqlalchemy.text(
                'DELETE FROM reviews WHERE id=:id'
            )

        result = conn.execute(stmt, parameters={'id': id})
        conn.commit()
        
        if result.rowcount == 1:
            return ('', 204)
        else:
            return ERROR_REVIEW_NOT_FOUND, 404


# list all reviews for a user
@app.route('/users/<int:id>/' + REVIEWS, methods=['GET'])
def get_review_by_user(id):
    with db.connect() as conn:
        stmt = sqlalchemy.text(
                'SELECT * FROM reviews WHERE user_id = :user_id'
            )
        
        result = conn.execute(stmt, parameters={'user_id': id})
        conn.commit()

        reviews = []
        

        for row in result.fetchall():
            review = row._asdict()
            
            review['self'] = request.url_root + f"reviews/{review['id']}"
            business_url = request.url_root + f"businesses/{review['business_id']}"

            updated_review = {
                "id": review['id'],
                "user_id": review['user_id'],
                "business": business_url,
                "stars": review['stars'],
                "review_text": review['review_text'],
                "self": review['self']
            }
            reviews.append(updated_review)

        return reviews






# list all reviews
@app.route('/' + REVIEWS, methods=['GET'])
def get_reviews():
    with db.connect() as conn:
        # pagination - create offset and limit
        offset = request.args.get('offset', default=0, type=int)
        limit = request.args.get('limit', default=3, type=int)

        
        stmt = sqlalchemy.text(
            'SELECT * FROM reviews LIMIT :limit OFFSET :offset'
        )
        rows = conn.execute(stmt, {'limit': limit + 1, 'offset': offset}).fetchall()
        
        reviews = []
        for row in rows[:limit]:  
            review = row._asdict()
            # review['zip_code'] = int(business['zip_code'])
            
            
            root_url = request.url_root
            review['self'] = f"{root_url}reviews/{review['id']}"
            
            reviews.append(review)

        
        response_data = {'entries': reviews}
        if len(rows) > limit:
            next_offset = offset + limit
            next_url = f"{request.base_url}?offset={next_offset}&limit={limit}"
            response_data['next'] = next_url

        return response_data, 200










if __name__ == '__main__':
    init_db()
    create_table(db)
    app.run(host='0.0.0.0', port=8080, debug=True)
