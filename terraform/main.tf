# Main Infrastructure Configuration for Placement Tracker EC2 Instance

# 1. Look up the latest official Amazon Linux 2023 AMI
# Dynamically selects x86_64 or arm64 architecture based on the selected instance_type.
locals {
  is_arm_instance = can(regex("^t4g\\.", var.instance_type))
  ami_arch        = local.is_arm_instance ? "arm64" : "x86_64"
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-${local.ami_arch}"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
}

# 2. User Data Script: Automates system updates, Docker, Docker Compose, and SSM agent setup
locals {
  user_data = <<-EOF
    #!/bin/bash
    set -xe

    # Update all system packages
    dnf update -y

    # Install Docker and Git
    dnf install -y docker git

    # Start and enable Docker on boot
    systemctl start docker
    systemctl enable docker

    # Add ec2-user to docker group to run docker commands without sudo
    usermod -aG docker ec2-user

    # Install Docker Compose CLI plugin (v2)
    DOCKER_CONFIG=/usr/local/lib/docker
    mkdir -p $DOCKER_CONFIG/cli-plugins
    ARCH=$(uname -m)
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$ARCH" -o $DOCKER_CONFIG/cli-plugins/docker-compose
    chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

    # Symlink docker-compose for backward compatibility
    ln -s $DOCKER_CONFIG/cli-plugins/docker-compose /usr/local/bin/docker-compose || true

    # Ensure AWS Systems Manager (SSM) agent is active
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent

    echo "Docker and Docker Compose installation complete!"
  EOF
}

# 3. EC2 Instance Resource
resource "aws_instance" "web_server" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [aws_security_group.web_sg.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_instance_profile.name
  associate_public_ip_address = true

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true

    tags = {
      Name = "${var.project_name}-root-volume"
    }
  }

  user_data                   = local.user_data
  user_data_replace_on_change = true

  tags = {
    Name = "${var.project_name}-ec2"
  }
}
