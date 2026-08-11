variable "instance_name" {
  description = "Value of the EC2 instances's Name tag."
  type        = string
  default     = "terraform"
}

variable "instance_type" {
  description = "The EC2 instance's type"
  type        = string
  default     = "t3.micro"
}

variable "repo_url" {
  description = "Public git repo containing the site/ folder"
  type        = string
  default     = "https://github.com/Alexcarync/terraform-aws-status"
}