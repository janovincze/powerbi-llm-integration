{{
    config(
        materialized='view',
        tags=['staging', 'daily']
    )
}}

/*
    Staging model for customer data.

    This model:
    - Renames columns to standard naming convention
    - Casts data types appropriately
    - Filters out test/invalid records
    - Adds basic data quality flags

    Source: raw.raw_customers
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_customers') }}
),

cleaned AS (
    SELECT
        -- Primary key
        customer_id,

        -- Attributes
        TRIM(UPPER(customer_name)) AS customer_name,
        LOWER(TRIM(email)) AS email,
        COALESCE(segment, 'Unknown') AS segment,
        COALESCE(region, 'Unknown') AS region,

        -- Dates
        created_at::TIMESTAMP_NTZ AS created_at,
        updated_at::TIMESTAMP_NTZ AS updated_at,

        -- Metadata
        _loaded_at,

        -- Data quality flags
        CASE
            WHEN email IS NULL OR email NOT LIKE '%@%.%' THEN FALSE
            ELSE TRUE
        END AS is_valid_email,

        CASE
            WHEN customer_name IS NULL OR LENGTH(customer_name) < 2 THEN FALSE
            ELSE TRUE
        END AS is_valid_name

    FROM source

    -- Filter out test records
    WHERE customer_id IS NOT NULL
      AND (email NOT LIKE '%@test.%' OR email IS NULL)
      AND customer_name NOT ILIKE '%test%'
)

SELECT * FROM cleaned
