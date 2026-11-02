# Security Group Configuration for Placement Tracker EC2 Instance

resource "aws_security_group" "web_sg" {
  name_prefix = "${var.project_name}-ec2-sg-"
  description = "Security group for Placement Tracker EC2 instance: allows public HTTP and restricts sensitive ports"
  vpc_id      = var.vpc_id

  # Ingress: Allow public HTTP access on port 80 (Frontend web server)
  ingress {
    description      = "Public HTTP access to frontend"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }


  # NOTE: Flask Backend port 5001 is deliberately NOT exposed to the public Internet.
  # Nginx reverse proxies traffic internally within the host, protecting the backend.

  # Ingress: Restricted SSH access (port 22) ONLY if admin_ssh_cidr is explicitly provided.
  # Unrestricted SSH (0.0.0.0/0) is strictly blocked.
  # Administration is managed via AWS Systems Manager Session Manager (SSM) without needing port 22 open.
  dynamic "ingress" {
    for_each = var.admin_ssh_cidr != "" ? [var.admin_ssh_cidr] : []
    content {
      description = "Restricted SSH access from admin IP"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  # Egress: Allow all outbound traffic so EC2 can update packages, install Docker, and reach SSM endpoints
  egress {
    description      = "Allow all outbound traffic"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "${var.project_name}-web-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}
