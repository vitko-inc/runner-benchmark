output "vpc_id" { value = aws_vpc.this.id }
output "subnet_id" { value = aws_subnet.public.id }
output "security_group_id" { value = aws_security_group.runner.id }
output "launch_template_id" {
  value = try(aws_launch_template.runner[0].id, "")
}
