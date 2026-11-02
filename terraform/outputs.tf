# Terraform Outputs for Placement Tracker Infrastructure

output "instance_id" {
  description = "The ID of the provisioned EC2 instance."
  value       = aws_instance.web_server.id
}

output "public_ip" {
  description = "The public IPv4 address assigned to the EC2 instance."
  value       = aws_instance.web_server.public_ip
}

output "public_dns" {
  description = "The public DNS name assigned to the EC2 instance."
  value       = aws_instance.web_server.public_dns
}

output "application_url" {
  description = "Public URL to access the College Placement Tracker frontend web application."
  value       = "http://${aws_instance.web_server.public_ip}"
}

output "security_group_id" {
  description = "The ID of the security group attached to the EC2 instance."
  value       = aws_security_group.web_sg.id
}

output "ssm_connect_command" {
  description = "AWS CLI command to connect to the EC2 instance via Systems Manager Session Manager (no SSH key needed)."
  value       = "aws ssm start-session --target ${aws_instance.web_server.id} --region ${var.aws_region}"
}
