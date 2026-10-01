variable "project" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  type    = string
  default = "us-east4"
}

variable "zones" {
  description = "VMs are spread round-robin across these zones."
  type        = list(string)
  default     = ["us-east4-a", "us-east4-b", "us-east4-c"]
}

variable "name" {
  description = "Name prefix; VM names are <name>-NN and double as runner names."
  type        = string
  default     = "rb-gce-pool"
}

variable "subnet_cidr" {
  type    = string
  default = "10.81.0.0/20"
}

variable "pool_size" {
  description = "Number of runner VMs."
  type        = number
  default     = 20
}

variable "machine_type" {
  type    = string
  default = "n4d-standard-2"
}

variable "image" {
  description = "Runner image (self link or projects/<p>/global/images/<name>) from image/bake_gcp.sh. Empty = network only."
  type        = string
  default     = ""
}

variable "disk_gb" {
  type    = number
  default = 75
}

variable "disk_type" {
  description = "N4D machine types only accept Hyperdisk; pd-* types are rejected."
  type        = string
  default     = "hyperdisk-balanced"
}

variable "disk_iops" {
  description = "Hyperdisk Balanced IOPS (3000 = included baseline)."
  type        = number
  default     = 3000
}

variable "disk_throughput_mibps" {
  description = "Hyperdisk Balanced throughput (140 = included baseline)."
  type        = number
  default     = 140
}

variable "github_repo" {
  description = "owner/name of the repository the runners register to."
  type        = string
}

variable "runner_labels" {
  description = "Comma-separated custom runner labels."
  type        = string
  default     = "rb-gce-pool"
}

variable "registration_token" {
  description = "Repository runner registration token (valid 1 h). Mint locally right before apply."
  type        = string
  default     = ""
  sensitive   = true
}

variable "labels" {
  type    = map(string)
  default = { "rb-owner" = "runner-benchmark" }
}
