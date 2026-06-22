-- Stage 1 current SQLite schema snapshot
-- Date: 2026-06-17
-- Database: database/applications.db
-- Table counts at snapshot time:
-- applications: 7
-- companies: 0
-- contacts: 0
-- documents: 0

CREATE TABLE applications (
            application_id TEXT PRIMARY KEY,

            date_created TEXT NOT NULL,
            date_updated TEXT NOT NULL,

            company_name TEXT,
            company_size TEXT,
            company_industry TEXT,
            company_website TEXT,
            company_linkedin TEXT,
            career_page_url TEXT,

            job_title TEXT,
            job_domain TEXT,
            seniority_level TEXT,
            contract_type TEXT,
            job_length TEXT,
            salary TEXT,
            location TEXT,
            remote_policy TEXT,
            relocation_required TEXT,

            key_responsibilities TEXT,
            required_skills TEXT,
            preferred_qualifications TEXT,
            detected_language TEXT,
            raw_job_description TEXT,

            source_platform TEXT,
            application_channel TEXT,
            job_url TEXT,
            status TEXT,
            date_applied TEXT,
            follow_up_date TEXT,
            contact_person TEXT,
            contact_url TEXT,
            notes TEXT,

            recommended_cv TEXT,
            selected_cv TEXT,
            cv_confidence_score REAL,
            cv_recommendation_reason TEXT,
            cv_matched_keywords TEXT,

            motivation_letter_required INTEGER,
            motivation_letter_language TEXT,
            motivation_letter_file TEXT,

            form_answers_file TEXT,

            google_sheet_row_id TEXT,

            archived INTEGER DEFAULT 0
        );

CREATE TABLE companies (
            company_id TEXT PRIMARY KEY,

            date_created TEXT NOT NULL,
            date_updated TEXT NOT NULL,

            company_name TEXT NOT NULL,
            company_size TEXT,
            company_industry TEXT,
            company_website TEXT,
            company_linkedin TEXT,
            career_page_url TEXT,

            country TEXT,
            city TEXT,

            source TEXT,
            source_url TEXT,

            notes TEXT
        );

CREATE TABLE contacts (
            contact_id TEXT PRIMARY KEY,
            company_id TEXT,

            date_created TEXT NOT NULL,
            date_updated TEXT NOT NULL,

            full_name TEXT,
            role_title TEXT,
            department TEXT,
            email TEXT,
            linkedin_url TEXT,

            source_type TEXT,
            source_url TEXT,
            manually_verified INTEGER DEFAULT 0,

            notes TEXT,

            FOREIGN KEY(company_id) REFERENCES companies(company_id)
        );

CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,

            document_type TEXT,
            domain TEXT,
            label TEXT,
            file_path TEXT,
            language TEXT,
            active INTEGER DEFAULT 1,
            version TEXT,
            notes TEXT
        );
