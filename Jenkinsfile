pipeline {
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        AWS_ACCOUNT_ID = credentials('aws-account-id')
        ECR_REPOSITORY = 'ecommerce-cart-staging'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Identify Build') {
            steps {
                script {
                    echo "Branch: ${env.BRANCH_NAME}"
                    echo "PR Number: ${env.CHANGE_ID}"
                    echo "PR Target: ${env.CHANGE_TARGET}"
                }
            }
        }

        stage('PR - Validation') {
            when {
                allOf {
                    changeRequest()
                    expression {
                        return env.CHANGE_TARGET?.startsWith('release/')
                    }
                }
            }

            parallel {
                stage('Gitleaks') {
                    steps {
                        sh '''
                            set -eu

                            gitleaks git . \
                            --redact \
                            --exit-code 1
                        '''
                    }
                }

                stage('Pytest') {
                    steps {
                        sh '''
                            set -eu
                            python3 -m venv .venv
                            .venv/bin/python -m pip install -r requirements.txt
                            .venv/bin/python -m pip install pytest
                            .venv/bin/python -m pytest tests/unit/ -v
                            .venv/bin/python -m pytest tests/api/ -v
                        '''
                    }
                }

                stage('Trivy FS Scan') {
                    steps {
                        sh '''
                            set -eu

                            trivy fs \
                                --scanners vuln,secret,misconfig \
                                --severity HIGH,CRITICAL \
                                --exit-code 0 \
                                --skip-dirs .venv \
                                --skip-dirs .git \
                                --format table \
                                .
                        '''
                    }
                }

            }

        }

        stage('Release - Code Quality Validation') {

            when {
                allOf {
                    not {
                        changeRequest()
                    }
                    expression {
                        return env.BRANCH_NAME?.startsWith('release/')
                    }
                }  
            }

            stages {

                stage('Test Coverage') {
                    steps {
                        sh '''
                            set -eu

                            python3 -m venv .venv
                            .venv/bin/python -m pip install -r requirements.txt
                            .venv/bin/python -m pip install pytest pytest-cov

                            .venv/bin/python -m pytest tests/unit/ tests/api/ \
                                --cov=app \
                                --cov-report=term-missing \
                                --cov-report=xml:coverage.xml
                        '''
                    }
                }

                stage('SonarQube Analysis') {
                    steps {
                        script {
                            def scannerHome = tool 'SonarScanner'

                            withSonarQubeEnv('SonarQube-Server') {
                                sh """
                                    ${scannerHome}/bin/sonar-scanner \
                                    -Dsonar.projectKey=ecommerce-cart-staging \
                                    -Dsonar.sources=app,alembic \
                                    -Dsonar.tests=tests \
                                    -Dsonar.python.version=3.13 \
                                    -Dsonar.python.coverage.reportPaths=coverage.xml \
                                    -Dsonar.coverage.exclusions=alembic/**
                                """
                            }
                        }
                    }
                }

                stage('SonarQube Quality Gate') {
                    steps {
                        timeout(time: 10, unit: 'MINUTES') {
                            waitForQualityGate abortPipeline: true
                        }
                    }
                }
            }
        }

        stage('Release - Docker Build and ECR Push') {

            when {
                allOf {
                    not {
                        changeRequest()
                    }
                    expression {
                        return env.BRANCH_NAME?.startsWith('release/')
                    }
                }
            }

            steps {
                script {

                    def IMAGE_TAG = sh(
                        script: 'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()

                    def ECR_REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"

                    def IMAGE_URI = "${ECR_REGISTRY}/${env.ECR_REPOSITORY}:${IMAGE_TAG}"

                    echo "Building Docker Image: ${IMAGE_URI}"

                    sh """
                        set -eu

                        docker build \
                            --platform linux/amd64 \
                            --provenance=false \
                            --sbom=false \
                            -t '${IMAGE_URI}' \
                            .

                        aws ecr get-login-password \
                            --region '${env.AWS_REGION}' |
                            docker login \
                                --username AWS \
                                --password-stdin '${ECR_REGISTRY}'

                        docker push '${IMAGE_URI}'
                    """

                    echo "Image pushed successfully: ${IMAGE_URI}"
                }
            }
        }

    }
}