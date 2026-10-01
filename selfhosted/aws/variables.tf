variable "region" {
  type    = string
  default = "us-east-1"
}

variable "availability_zone" {
  type    = string
  default = "us-east-1a"
}

variable "name" {
  description = "Name prefix for all resources."
  type        = string
  default     = "rb-ec2-eph"
}

variable "vpc_cidr" {
  type    = string
  default = "10.80.0.0/16"
}

variable "instance_type" {
  type    = string
  default = "m8a.large"
}

variable "root_volume_gb" {
  type    = number
  default = 75
}

variable "ami_id" {
  description = "Runner AMI produced by image/bake_aws.sh. Empty = network only."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags applied to every resource (the launcher adds per-job tags)."
  type        = map(string)
  default     = { "rb-owner" = "runner-benchmark" }
}
