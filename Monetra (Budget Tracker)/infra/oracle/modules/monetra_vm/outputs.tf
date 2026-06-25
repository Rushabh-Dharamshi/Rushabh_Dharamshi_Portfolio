output "instance_id" {
  description = "Created VM OCID."
  value       = oci_core_instance.monetra.id
}

output "public_ip" {
  description = "Public IP address for SSH and production checks."
  value       = oci_core_instance.monetra.public_ip
}

output "ssh_command" {
  description = "SSH command template."
  value       = "ssh -i <private-key-path> opc@${oci_core_instance.monetra.public_ip}"
}

output "vcn_id" {
  description = "Created VCN OCID."
  value       = oci_core_vcn.monetra.id
}

output "subnet_id" {
  description = "Created public subnet OCID."
  value       = oci_core_subnet.public.id
}
