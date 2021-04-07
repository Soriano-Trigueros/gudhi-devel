/*    This file is part of the Gudhi Library - https://gudhi.inria.fr/ - which is released under MIT.
 *    See file LICENSE or go to https://gudhi.inria.fr/licensing/ for full license details.
 *    Author(s):       Vincent Rouvreau
 *
 *    Copyright (C) 2016 Inria
 *
 *    Modification(s):
 *      - YYYY/MM Author: Description of the modification
 */

#ifndef INCLUDE_ALPHA_COMPLEX_INTERFACE_H_
#define INCLUDE_ALPHA_COMPLEX_INTERFACE_H_

#include "Alpha_complex_factory.h"
#include <gudhi/Alpha_complex_options.h>

#include "Simplex_tree_interface.h"

#include <iostream>
#include <vector>
#include <string>
#include <memory>  // for std::unique_ptr

namespace Gudhi {

namespace alpha_complex {

class Alpha_complex_interface {
 public:
  Alpha_complex_interface(const std::vector<std::vector<double>>& points,
                          const std::vector<double>& weights,
                          bool fast_version, bool exact_version)
  : empty_point_set_(points.size() == 0) {
    const bool weighted = (weights.size() > 0);
    if (fast_version) {
      if (weighted) {
        alpha_ptr_ = std::make_unique<Inexact_alpha_complex_dD<true>>(points, weights, exact_version);
      } else {
        alpha_ptr_ = std::make_unique<Inexact_alpha_complex_dD<false>>(points, exact_version);
      }
    } else {
      if (weighted) {
        alpha_ptr_ = std::make_unique<Exact_alpha_complex_dD<true>>(points, weights, exact_version);
      } else {
        alpha_ptr_ = std::make_unique<Exact_alpha_complex_dD<false>>(points, exact_version);
      }
    }
  }

  std::vector<double> get_point(int vh) {
    return alpha_ptr_->get_point(vh);
  }

  void create_simplex_tree(Simplex_tree_interface<>* simplex_tree, double max_alpha_square,
                           bool default_filtration_value) {
    // Nothing to be done in case of an empty point set
    if (!empty_point_set_)
      alpha_ptr_->create_simplex_tree(simplex_tree, max_alpha_square, default_filtration_value);
  }

 private:
  std::unique_ptr<Abstract_alpha_complex> alpha_ptr_;
  bool empty_point_set_;
};

}  // namespace alpha_complex

}  // namespace Gudhi

#endif  // INCLUDE_ALPHA_COMPLEX_INTERFACE_H_
