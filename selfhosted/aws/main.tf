# Ephemeral EC2 runner baseline: network + launch template.
# One fresh VM per job is launched from the launch template by ec2_launcher.py.
# The subnet is public (egress via an internet gateway, no NAT); the security
# group has no inbound rules.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "local" {}
}

provider "aws" {
  region = var.region
  default_tags {
    tags = var.tags
  }
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.name}-vpc" }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${var.name}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, 0)
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name}-public" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
  tags = { Name = "${var.name}-public" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Egress only: no ingress blocks at all.
resource "aws_security_group" "runner" {
  name        = "${var.name}-runner"
  description = "CI runners: egress only"
  vpc_id      = aws_vpc.this.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.name}-runner" }
}

# The runner AMI is baked separately (image/bake_aws.sh) and referenced by ID.
# The launch template is only created once an AMI ID is supplied.
data "aws_ami" "runner" {
  count  = var.ami_id == "" ? 0 : 1
  owners = ["self"]
  filter {
    name   = "image-id"
    values = [var.ami_id]
  }
}

resource "aws_launch_template" "runner" {
  count                                = var.ami_id == "" ? 0 : 1
  name                                 = "${var.name}-runner"
  image_id                             = data.aws_ami.runner[0].id
  instance_type                        = var.instance_type
  instance_initiated_shutdown_behavior = "terminate"
  update_default_version               = true

  block_device_mappings {
    device_name = data.aws_ami.runner[0].root_device_name
    ebs {
      volume_type           = "gp3"
      volume_size           = var.root_volume_gb
      iops                  = 3000
      throughput            = 125
      delete_on_termination = true
      encrypted             = true
    }
  }

  network_interfaces {
    device_index                = 0
    subnet_id                   = aws_subnet.public.id
    security_groups             = [aws_security_group.runner.id]
    associate_public_ip_address = true
    delete_on_termination       = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  tag_specifications {
    resource_type = "instance"
    tags          = merge(var.tags, { Name = "${var.name}-runner" })
  }
  tag_specifications {
    resource_type = "volume"
    tags          = var.tags
  }
}

# All-in cost (METHOD.md, "Cost"): VPC flow logs measure each runner's internet egress, split
# from traffic to S3 in the same region (free), by the cost collector (cost_ec2.py --flow-logs).
data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "flowlogs" {
  bucket        = "${var.name}-flowlogs-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "flowlogs" {
  bucket                  = aws_s3_bucket.flowlogs.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "flowlogs" {
  bucket = aws_s3_bucket.flowlogs.id
  rule {
    id     = "expire"
    status = "Enabled"
    filter {}
    expiration { days = 30 }
  }
}

resource "aws_flow_log" "runner" {
  vpc_id                   = aws_vpc.this.id
  traffic_type             = "ALL"
  log_destination_type     = "s3"
  log_destination          = aws_s3_bucket.flowlogs.arn
  max_aggregation_interval = 60
  log_format               = "$${version} $${interface-id} $${instance-id} $${srcaddr} $${dstaddr} $${bytes} $${start} $${end} $${flow-direction} $${pkt-dst-aws-service} $${action}"
}
