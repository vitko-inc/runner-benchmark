# Persistent GCE runner pool baseline: N always-on VMs, each with one
# non-ephemeral GitHub Actions runner registered to a single repository.
# pool_size = 0 deletes all VMs (and deregisters their runners first).

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
  backend "local" {}
}

provider "google" {
  project = var.project
  region  = var.region
}

resource "google_compute_network" "this" {
  name                    = "${var.name}-net"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "this" {
  name          = "${var.name}-subnet"
  network       = google_compute_network.this.id
  region        = var.region
  ip_cidr_range = var.subnet_cidr
}

# No firewall rules are defined: a custom VPC denies all ingress by default and
# allows all egress. VMs get an ephemeral external IP for egress (no NAT).

resource "google_compute_instance" "runner" {
  count        = var.image == "" ? 0 : var.pool_size
  name         = format("%s-%02d", var.name, count.index + 1)
  zone         = element(var.zones, count.index)
  machine_type = var.machine_type
  labels       = var.labels

  boot_disk {
    auto_delete = true
    initialize_params {
      image                  = var.image
      size                   = var.disk_gb
      type                   = var.disk_type
      provisioned_iops       = var.disk_type == "hyperdisk-balanced" ? var.disk_iops : null
      provisioned_throughput = var.disk_type == "hyperdisk-balanced" ? var.disk_throughput_mibps : null
      labels                 = var.labels
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.this.id
    access_config {}
  }

  # No service account: the VM holds no cloud identity.
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  metadata = {
    startup-script         = file("${path.module}/startup.sh")
    rb-repo                = var.github_repo
    rb-labels              = var.runner_labels
    rb-registration-token  = var.registration_token
    block-project-ssh-keys = "true"
  }

  lifecycle {
    # A registration token is only needed the first time a VM boots.
    ignore_changes = [metadata["rb-registration-token"]]
  }

  # Remove the runner registration from the repository before the VM is deleted.
  # Uses the operator's local `gh` login; nothing is sent to the VM.
  provisioner "local-exec" {
    when       = destroy
    on_failure = continue
    command    = "${path.module}/deregister.sh '${self.metadata["rb-repo"]}' '${self.name}'"
  }
}
