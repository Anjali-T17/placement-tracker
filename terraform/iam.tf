# IAM Role and Instance Profile for AWS Systems Manager (SSM) Access

# 1. IAM Role that EC2 service can assume
resource "aws_iam_role" "ec2_ssm_role" {
  name_prefix = "${var.project_name}-ssm-role-"
  description = "IAM role allowing EC2 to communicate with AWS Systems Manager (SSM)"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ssm-role"
  }
}

# 2. Attach the AWS managed policy AmazonSSMManagedInstanceCore
# This enables browser-based terminal access and SSM Session Manager without open inbound ports or SSH keys.
resource "aws_iam_role_policy_attachment" "ssm_core_attachment" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# 3. IAM Instance Profile required to attach the IAM role to the EC2 instance
resource "aws_iam_instance_profile" "ec2_instance_profile" {
  name_prefix = "${var.project_name}-instance-profile-"
  role        = aws_iam_role.ec2_ssm_role.name

  tags = {
    Name = "${var.project_name}-instance-profile"
  }
}
