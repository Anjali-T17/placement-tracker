pipeline {
    agent any

    environment {
        // Ensure Homebrew, Docker, and Python 3.11 binaries are accessible in Jenkins PATH
        PATH = "/Users/anjali/.docker/bin:/opt/homebrew/bin:/opt/homebrew/opt/python@3.11/libexec/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${env.PATH}"
        PYTHON = "/opt/homebrew/bin/python3.11"
    }

    stages {
        stage('GitHub Checkout') {
            steps {
                echo 'Stage 1: Checking out latest code from GitHub main branch...'
                sh '''
                    if [ -d ".git" ]; then
                        git fetch origin main
                        git reset --hard origin/main
                    else
                        git clone -b main https://github.com/Anjali-T17/placement-tracker.git .
                    fi
                '''
            }
        }

        stage('Backend Dependency Installation') {
            steps {
                echo 'Stage 2: Setting up Python 3.11 virtual environment and installing dependencies...'
                sh '''
                    ${PYTHON} -m venv .jenkins_venv
                    . .jenkins_venv/bin/activate
                    pip install --upgrade pip
                    pip install -r backend/requirements.txt
                '''
            }
        }

        stage('Backend Unit Testing') {
            steps {
                echo 'Stage 3: Running all 41 backend automated unit tests...'
                sh '''
                    . .jenkins_venv/bin/activate
                    cd backend
                    python -m unittest discover -s tests -v
                '''
            }
        }

        stage('Docker Backend Image Build') {
            steps {
                echo 'Stage 4: Building Backend Docker image from backend/Dockerfile...'
                sh 'docker build -t placement-backend:jenkins ./backend'
            }
        }

        stage('Docker Frontend Image Build') {
            steps {
                echo 'Stage 5: Building Frontend Docker image from frontend/Dockerfile...'
                sh 'docker build -t placement-frontend:jenkins ./frontend'
            }
        }

        stage('Docker Compose Validation') {
            steps {
                echo 'Stage 6: Validating Docker Compose configuration...'
                sh 'docker compose config'
            }
        }

        stage('Pipeline Success') {
            steps {
                echo '==================================================='
                echo '  College Placement Tracker: CI Pipeline Passed!   '
                echo '  - All 41 Backend Tests Passed with Python 3.11   '
                echo '  - Backend & Frontend Docker Images Built Cleanly '
                echo '  - Docker Compose Validated Successfully          '
                echo '==================================================='
            }
        }
    }

    post {
        always {
            echo 'Cleaning up Jenkins virtual environment...'
            sh 'rm -rf .jenkins_venv'
        }
        success {
            echo 'Jenkins Pipeline completed successfully!'
        }
        failure {
            echo 'Jenkins Pipeline failed! Check the console logs above for details.'
        }
    }
}
