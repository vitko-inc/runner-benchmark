output "network" { value = google_compute_network.this.name }
output "subnetwork" { value = google_compute_subnetwork.this.name }
output "runners" {
  value = [for i in google_compute_instance.runner : { name = i.name, zone = i.zone, id = i.instance_id }]
}
