# Input Variables for Placement Tracker Infrastructure

variable "aws_region" {
  type        = string
  description = "AWS Region where the infrastructure will be provisioned."
  default     = "ap-southeast-2"
}

variable "vpc_id" {
  type        = string
  description = "Existing VPC ID to deploy the EC2 instance and security group into."
  default     = "vpc-005bb88d77ebfd4f7"
}

variable "subnet_id" {
  type        = string
  description = "Existing public Subnet ID where the EC2 instance will be launched."
  default     = "subnet-0d4fa31cc4cfac75f"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type for running the Dockerized application."
  default     = "t3.small"
}

variable "project_name" {
  type        = string
  description = "Project name prefix used for resource naming and tagging."
  default     = "placement-tracker"
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g., dev, staging, prod)."
  default     = "dev"
}

variable "admin_ssh_cidr" {
  type        = string
  description = "Optional specific IP or CIDR block allowed for SSH access (e.g. '203.0.113.25/32'). Leave empty to keep port 22 completely closed. EC2 administration is handled securely via AWS Systems Manager (SSM) without open inbound ports."
  default     = ""
}

variable "root_volume_size" {
  type        = number
  description = "Size of the root EBS volume in GB."
  default     = 20
}
